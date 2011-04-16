import sys
import os
import errno
import socket
from microactor.utils import Deferred, safe_import
fcntl = safe_import("fcntl")


class TransportError(Exception):
    pass
class TransportClosed(TransportError):
    pass
class TransportDetached(TransportError):
    pass
class ReadRequiresMoreData(TransportError):
    pass


class InvalidFile(object):
    __slots__ = ["_exc"]
    closed = True
    def __init__(self, exc):
        self._exc = exc
    def __nonzero__(self):
        return False
    __bool__ = __nonzero__
    def close(self):
        pass
    def __int__(self):
        raise self._exc
    def fileno(self):
        raise self._exc
    def __getattr__(self, name):
        raise self._exc

ClosedFile = InvalidFile(TransportClosed)
DetachedFile = InvalidFile(TransportDetached)


class BaseTransport(object):
    __slots__ = ["reactor", "_fileno"]
    def __init__(self, reactor):
        self.reactor = reactor
        self._fileno = self.fileno()
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
            raise TransportError("overlapping reads")
        dfr = Deferred()
        if self._eof:
            dfr.set(None)
        else:
            self._read_req = (dfr, count)
            self.reactor.register_read(self)
        return dfr
    
    def write(self, data):
        if self._write_req:
            raise TransportError("overlapping writes")
        dfr = Deferred()
        self._write_req = (dfr, data)
        self.reactor.register_write(self)
        return dfr
    
    def on_read(self):
        if not self._read_req:
            self.reactor.unregister_read(self)
            return
        
        dfr, count = self._read_req
        try:
            if count <= 0:
                data = ""
            else:
                data = self._do_read(min(self.MAX_READ_SIZE, count))
        except ReadRequiresMoreData:
            return # don't unregister read and don't remove _read_req
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


class PipeTransport(StreamTransport):
    __slots__ = ["mode", "name", "_flush_dfr", "auto_flush"]
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
    def _unblock(cls, fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    def isatty(self):
        return self.fileobj.isatty()

    def flush(self):
        if not self._flush_dfr:
            self._flush_dfr = Deferred()
            self.reactor.register_write(self)
        return self._flush_dfr
    
    def _do_write(self, data):
        res = StreamTransport._do_write(self, data)
        if self.auto_flush or self._flush_dfr:
            self.fileobj.flush()
            if self._flush_dfr:
                self._flush_dfr.set()
                self._flush_dfr = None
        return res


class FileTransport(PipeTransport):
    __slots__ = []
    def seek(self, pos, whence = 0):
        self.fileobj.seek(pos, whence)
    def tell(self):
        return self.fileobj.tell()


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
        return self.fileobj.send(data)


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
            self.sock.close()
            self.sock = ClosedFile
    def detach(self):
        if self.sock:
            self._unregister()
            self.sock = DetachedFile


class ListeningSocketTransport(BaseSocketTransport):
    __slots__ = ["_accept_dfr"]
    def __init__(self, reactor, sock):
        BaseSocketTransport.__init__(self, reactor, sock)
        self._accept_dfr = None
    def accept(self):
        if self._accept_dfr:
            raise TransportError("overlapping accept")
        self._accept_dfr = Deferred()
        self.reactor.register_read(self)
        return self._accept_dfr
    def on_read(self):
        if not self._accept_dfr:
            self.reactor.unregister_read(self)
            return
        sock, _ = self.sock.accept()
        dfr = self._accept_dfr
        self._accept_dfr = None
        dfr.set(SocketStreamTransport(self.reactor, sock))


class ConnectingSocketTransport(BaseSocketTransport):
    __slots__ = ["addr", "connected_dfr", "_connecting"]
    def __init__(self, reactor, sock, addr):
        BaseSocketTransport.__init__(self, reactor, sock)
        self.addr = addr
        self.connected_dfr = Deferred()
        self._connecting = False
    
    def connect(self, timeout = None):
        if self._connecting:
            raise TransportError("already connecting")
        self._connecting = True
        if timeout is not None:
            self.reactor.jobs.schedule(timeout, self.cancel)
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





