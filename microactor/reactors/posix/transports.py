import sys
import os
import errno
import socket
from microactor.utils import ReactorDeferred, reactive, rreturn, safe_import
from ..transports import ClosedFile, DetachedFile
from ..transports import TransportError, ReadRequiresMoreData, OverlappingRequestError
fcntl = safe_import("fcntl")
ssl = safe_import("ssl")


#===============================================================================
# Base
#===============================================================================
class BaseTransport(object):
    __slots__ = ["reactor"]
    def __init__(self, reactor):
        self.reactor = reactor
    def fileno(self):
        raise NotImplementedError()
    def close(self):
        raise NotImplementedError()
    def detach(self):
        raise NotImplementedError()
    def _unregister(self):
        self.reactor.unregister_read(self)
        self.reactor.unregister_write(self)

    def on_read(self):
        pass
    def on_write(self):
        pass
    def on_error(self, exc):
        pass


class WakeupTransport(BaseTransport):
    __slots__ = ["wsock", "rsock", "auto_reset", "_set"]
    def __init__(self, reactor, auto_reset = True):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("localhost", 0))
        listener.listen(1)
        self.wsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.wsock.connect(listener.getsockname())
        self.rsock, _ = listener.accept()
        listener.close()
        self.auto_reset = auto_reset
        self._set = False
        BaseTransport.__init__(self, reactor)
    def fileno(self):
        return self.rsock.fileno()
    def close(self):
        if self.wsock:
            self.wsock.shutdown(socket.SHUT_RDWR)
            self.wsock.close()
            self.wsock = ClosedFile
        if self.rsock:
            self.rsock.shutdown(socket.SHUT_RDWR)
            self.rsock.close()
            self.rsock = ClosedFile
    def on_read(self):
        if self.auto_reset:
            self.reset()

    def set(self):
        if self._set:
            return
        self.wsock.send("x")
        self._set = True
    def reset(self):
        if not self._set:
            return
        self.rsock.recv(100)
        self._set = False


class StreamTransport(BaseTransport):
    __slots__ = ["fileobj", "_read_req", "_write_req", "_eof"]
    MAX_READ_SIZE = 16300
    MAX_WRITE_SIZE = 16300

    def __init__(self, reactor, fileobj):
        self.fileobj = fileobj
        self._read_req = None
        self._write_req = None
        self._eof = False
        BaseTransport.__init__(self, reactor)

    def fileno(self):
        return self.fileobj.fileno()
    def detach(self):
        if self.fileobj:
            self._unregister()
            self.fileobj = DetachedFile
    def close(self):
        if self.fileobj:
            self._unregister()
            self.fileobj.close()
            self.fileobj = ClosedFile

    def read(self, count):
        if self._read_req:
            raise OverlappingRequestError("overlapping reads")
        dfr = ReactorDeferred(self.reactor)
        if self._eof:
            dfr.set(None)
        elif count <= 0:
            dfr.set("")
        else:
            self._read_req = (dfr, count)
            self.reactor.register_read(self)
        return dfr

    def write(self, data):
        if self._write_req:
            raise OverlappingRequestError("overlapping writes")
        dfr = ReactorDeferred(self.reactor)
        self._write_req = (dfr, data)
        self.reactor.register_write(self)
        return dfr

    def on_read(self):
        if not self._read_req:
            self.reactor.unregister_read(self)
            return

        dfr, count = self._read_req
        try:
            data = self._do_read(min(self.MAX_READ_SIZE, count))
        except ReadRequiresMoreData:
            # don't unregister_read and don't remove _read_req
            return
        except Exception as ex:
            dfr.throw(ex)
        else:
            if not data:
                self._eof = True
                data = None
            dfr.set(data)
        self.reactor.unregister_read(self)
        self._read_req = None

    def on_write(self):
        if not self._write_req:
            self.reactor.unregister_write(self)
            return

        dfr, data = self._write_req
        try:
            if data:
                count = self._do_write(data[:self.MAX_WRITE_SIZE])
            else:
                count = 0
        except Exception as ex:
            data = None
            dfr.throw(ex)
        else:
            if count is None or count >= len(data):
                data = None
            else:
                data = data[count:]
                self._write_req = (dfr, data)
        if not data:
            dfr.set()
            self.reactor.unregister_write(self)
            self._write_req = None

    def _do_read(self, count):
        return self.fileobj.read(count)
    def _do_write(self, data):
        return self.fileobj.write(data)


#===============================================================================
# Pipes and Files
#===============================================================================
class PipeTransport(StreamTransport):
    #__slots__ = ["mode", "name", "_flush_dfr", "auto_flush"]
    def __init__(self, reactor, fileobj, mode, auto_flush = True):
        if mode not in ("r", "w", "rw"):
            raise ValueError("invalid mode")
        StreamTransport.__init__(self, reactor, fileobj)
        self.name = getattr(self.fileobj, "name", None)
        self.mode = mode
        self._flush_dfr = None
        self.auto_flush = auto_flush
        if "r" not in mode:
            self.read = self._wrong_mode
        if "w" not in mode:
            self.flush = self._wrong_mode
            self.write = self._wrong_mode
        if fcntl:
            self._unblock(self.fileno())

    @staticmethod
    def _wrong_mode(*args):
        raise IOError("wrong mode for operation")
    @staticmethod
    def _unblock(fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    def isatty(self):
        return self.fileobj.isatty()

    def flush(self):
        if not self._flush_dfr:
            self._flush_dfr = ReactorDeferred(self.reactor)
            self.reactor.register_write(self)
        return self._flush_dfr

    def _flush(self):
        self.fileobj.flush()
        os.fsync(self.fileno())
        if self._flush_dfr:
            self._flush_dfr.set()
            self._flush_dfr = None

    def on_write(self):
        StreamTransport.on_write(self)
        if self.auto_flush or self._flush_dfr:
            self._flush()


class FileTransport(PipeTransport):
    __slots__ = []
    def seek(self, pos, whence = 0):
        self.fileobj.seek(pos, whence)
    def tell(self):
        return self.fileobj.tell()


#===============================================================================
# Stream Sockets
#===============================================================================
class SocketStreamTransport(StreamTransport):
    __slots__ = []

    def __init__(self, reactor, sock):
        StreamTransport.__init__(self, reactor, sock)
        sock.setblocking(False)

    def getsockname(self):
        return self.fileno.getsockname()
    def getpeername(self):
        return self.fileobj.getpeername()

    def shutdown(self, mode = "rw"):
        if mode == "r":
            flags = socket.SHUT_RD
            self.reactor.unregister_read(self)
        elif mode == "w":
            flags = socket.SHUT_WR
            self.reactor.unregister_write(self)
        elif mode == "rw":
            flags = socket.SHUT_RDWR
            self._unregister()
        else:
            raise ValueError("invalid mode: %r" % (mode,))
        self.fileobj.shutdown(flags)

    def close(self):
        try:
            self.shutdown()
        except Exception:
            pass
        StreamTransport.close(self)

    def _do_read(self, count):
        try:
            return self.fileobj.recv(count)
        except socket.error as ex:
            if ex.errno in (errno.ECONNRESET, errno.ECONNABORTED):
                return ""  # EOF
            else:
                raise

    def _do_write(self, data):
        try:
            return self.fileobj.send(data)
        except socket.error as ex:
            if ex.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                return 0
            else:
                raise


class BaseSocketTransport(BaseTransport):
    __slots__ = ["sock"]
    def __init__(self, reactor, sock):
        self.sock = sock
        self.sock.setblocking(False)
        BaseTransport.__init__(self, reactor)
    def fileno(self):
        return self.sock.fileno()
    def close(self):
        if self.sock:
            self._unregister()
            self.sock.close()
            self.sock = ClosedFile
    def detach(self):
        if self.sock:
            self._unregister()
            self.sock = DetachedFile


class ListeningSocketTransport(BaseSocketTransport):
    __slots__ = ["_accept_dfr", "factory"]
    def __init__(self, reactor, sock, factory = SocketStreamTransport):
        BaseSocketTransport.__init__(self, reactor, sock)
        self._accept_dfr = None
        self.factory = factory
    def accept(self):
        if self._accept_dfr:
            raise OverlappingRequestError("overlapping accept")
        self._accept_dfr = ReactorDeferred(self.reactor)
        self.reactor.register_read(self)
        return self._accept_dfr
    def on_read(self):
        if not self._accept_dfr:
            self.reactor.unregister_read(self)
            return
        sock, _ = self.sock.accept()
        dfr = self._accept_dfr
        self._accept_dfr = None
        dfr.set(self.factory(self.reactor, sock))


class ConnectingSocketTransport(BaseSocketTransport):
    __slots__ = ["addr", "connected_dfr", "_connecting"]
    def __init__(self, reactor, sock, addr):
        BaseSocketTransport.__init__(self, reactor, sock)
        self.addr = addr
        self.connected_dfr = ReactorDeferred(self.reactor)
        self._connecting = False

    def connect(self, timeout = None):
        if self._connecting:
            raise OverlappingRequestError("already connecting")
        self._connecting = True
        if timeout is not None:
            self.reactor.jobs.schedule(timeout, self._cancel)
        self.reactor.register_write(self)
        self._attempt_connect()
        return self.connected_dfr

    def on_write(self):
        self._attempt_connect()

    def _attempt_connect(self):
        if self.connected_dfr.is_set():
            self.detach()
            return
        err = self.sock.connect_ex(self.addr)
        if err in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
            return
        if err == errno.EINVAL and sys.platform == "win32":
            return

        sock = self.sock
        self.detach()
        if err in (0, errno.EISCONN):
            self.connected_dfr.set(SocketStreamTransport(self.reactor, sock))
        else:
            self.connected_dfr.throw(socket.error(err, errno.errorcode[err]))

    def _cancel(self):
        if self.connected_dfr.is_set():
            return
        self.close()
        self.connected_dfr.throw(socket.timeout("connection timed out"))


#===============================================================================
# Datagram Sockets
#===============================================================================
class DatagramSocketTransport(BaseSocketTransport):
    __slots__ = []
    MAX_DATAGRAM_SIZE = 4096

    def __init__(self, reactor, sock):
        BaseSocketTransport.__init__(self, reactor, sock)
        self._read_req = None
        self._write_req = None

    def getsockname(self):
        return self.sock.getsockname()

    def recvfrom(self, count = -1):
        if self._read_req:
            raise OverlappingRequestError("overlapping recvfrom")
        dfr = ReactorDeferred(self.reactor)
        self._read_req = (dfr, count)
        self.reactor.register_read(self)
        return dfr

    def sendto(self, addr, data):
        if len(data) > self.MAX_DATAGRAM_SIZE:
            raise TransportError("data too long")
        if self._write_req:
            raise OverlappingRequestError("overlapping sendto")
        dfr = ReactorDeferred(self.reactor)
        self._write_req = (dfr, addr, data)
        self.reactor.register_write(self)
        return dfr

    def on_read(self):
        if not self._read_req:
            self.reactor.unregister_read(self)
            return

        dfr, count = self._read_req
        self.reactor.unregister_read(self)
        self._read_req = None

        if count < 0 or count > self.MAX_DATAGRAM_SIZE:
            count = self.MAX_DATAGRAM_SIZE
        try:
            data, addr = self.sock.recvfrom(count)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set((addr, data))

    def on_write(self):
        dfr, addr, data = self._write_req
        self.reactor.unregister_write(self)
        self._write_req = None

        try:
            count = self.sock.sendto(data, addr)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(count)


#===============================================================================
# SSL
#===============================================================================
class SslStreamTransport(SocketStreamTransport):
    __slots__ = []

    def getpeercert(self, binary_form = False):
        return self.fileobj.getpeercert(binary_form)

    def unwrap(self):
        s = self.fileobj.unwrap()
        self.detach()
        return SocketStreamTransport(self.reactor, s)

    def _do_read(self, count):
        try:
            return self.fileobj.recv(count)
        except ssl.SSLError as ex:
            if ex.errno == ssl.SSL_ERROR_WANT_READ:
                raise ReadRequiresMoreData
            elif ex.errno == ssl.SSL_ERROR_EOF:
                return "" # EOF
            else:
                raise
        except socket.error as ex:
            if ex.errno in (errno.ECONNRESET, errno.ECONNABORTED):
                return ""  # EOF
            else:
                raise


class SslHandshakingTransport(BaseSocketTransport):
    __slots__ = ["connected_dfr"]

    def __init__(self, reactor, sslsock):
        BaseSocketTransport.__init__(self, reactor, sslsock)
        self.connected_dfr = ReactorDeferred(self.reactor)

    def handshake(self):
        if not self.connected_dfr.is_set():
            self._handshake()
        return self.connected_dfr

    def _handshake(self):
        try:
            self.sock.do_handshake()
        except ssl.SSLError as ex:
            if ex.errno == ssl.SSL_ERROR_WANT_READ:
                self.reactor.register_read(self)
            elif ex.errno == ssl.SSL_ERROR_WANT_WRITE:
                self.reactor.register_write(self)
            else:
                self.connected_dfr.throw(ex)
        else:
            sock = self.sock
            self.detach()
            trns = SslStreamTransport(self.reactor, sock)
            self.connected_dfr.set(trns)

    def on_read(self):
        self.reactor.unregister_read(self)
        self._handshake()

    def on_write(self):
        self.reactor.unregister_write(self)
        self._handshake()


class SslListeninglSocketTransport(ListeningSocketTransport):
    __slots__ = []
    def __init__(self, reactor, sock):
        ListeningSocketTransport.__init__(self, reactor, sock, SslHandshakingTransport)

    @reactive
    def accept(self):
        handshaking_trns = yield ListeningSocketTransport.accept()
        trns = yield handshaking_trns.handshake()
        rreturn(trns)



