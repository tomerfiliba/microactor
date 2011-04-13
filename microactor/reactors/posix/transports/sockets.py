import socket
import errno
import sys
from .base import BaseTransport, StreamTransport, NeedMoreData
from microactor.utils import Deferred, reactive, rreturn, safe_import
from microactor.utils.colls import Queue
ssl = safe_import("ssl")



class BaseSocketTransport(BaseTransport):
    __slots__ = ["sock"]
    def __init__(self, reactor, sock):
        BaseTransport.__init__(self, reactor)
        self.sock = sock
        self.sock.setblocking(False)
    def detach(self):
        self._unregister()
        self.sock = None
    def close(self):
        if self.sock is None:
            return
        self._unregister()
        self.sock.close()
        self.sock = None
    def fileno(self):
        return self.sock.fileno()


#===============================================================================
# Stream Sockets
#===============================================================================

class StreamSocketTransport(StreamTransport):
    __slots__ = ["_local_addr", "_peer_addr"]
    _SHUTDOWN_MAP = {
        "r" : socket.SHUT_RD, 
        "w" : socket.SHUT_WR, 
        "rw" : socket.SHUT_RDWR
    }
    
    def __init__(self, reactor, sock):
        StreamTransport.__init__(self, reactor, sock)
        sock.setblocking(False)
        self._local_addr = None
        self._peer_addr = None

    @property
    def local_addr(self):
        if not self._local_addr:
            self._local_addr = self.fileobj.getsockname()
        return self._local_addr
    
    @property
    def peer_addr(self):
        if not self._peer_addr:
            self._peer_addr = self.fileobj.getpeername()
        return self._peer_addr
        
    def close(self):
        try:
            self.shutdown()
        except Exception:
            pass # will fail if fd has been closed
        StreamTransport.close(self)
    
    def shutdown(self, mode = "rw"):
        mode2 = self._SHUTDOWN_MAP[mode]
        self.fileobj.shutdown(mode2)
    
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


class ListeningSocketTransport(BaseSocketTransport):
    def __init__(self, reactor, sock, transport_factory):
        BaseSocketTransport.__init__(self, reactor, sock)
        self._local_addr = None
        self.transport_factory = transport_factory
        self.accept_queue = Queue()

    @property
    def local_addr(self):
        if not self._local_addr:
            self._local_addr = self.fileobj.getsockname()
        return self._local_addr
    
    def accept(self):
        self.reactor.register_read(self)
        dfr = Deferred()
        self.accept_queue.push(dfr)
        return dfr
    def on_read(self, hint):
        s, _ = self.sock.accept()
        trns = self.transport_factory(self.reactor, s)
        dfr = self.accept_queue.pop()
        dfr.set(trns)


class ConnectingSocketTransport(BaseSocketTransport):
    def __init__(self, reactor, sock, addr):
        BaseSocketTransport.__init__(self, reactor, sock)
        self.addr = addr
        self.connected_dfr = Deferred()

    def connect(self, timeout):
        if timeout is not None:
            self.reactor.jobs.schedule(timeout, self._cancel)
        self.reactor.register_write(self)
        self.sock.setblocking(False)
        self._attempt_connect()
        return self.connected_dfr
    
    def _attempt_connect(self):
        if self.connected_dfr.is_set():
            self._unregister()
            return
        err = self.sock.connect_ex(self.addr)
        if err in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
            return
        if err == errno.EINVAL and sys.platform == "win32":
            return
        
        self.reactor.unregister_write(self)
        if err in (0, errno.EISCONN):
            self.connected_dfr.set()
        else:
            self.connected_dfr.throw(socket.error(err, errno.errorcode[err]))
    
    def on_write(self, hint):
        self._attempt_connect()
    
    def _cancel(self, job):
        if self.connected_dfr.is_set():
            return
        self.close()
        self.connected_dfr.throw(socket.timeout("connection timed out"))

#===============================================================================
# UDP
#===============================================================================

class UdpTransport(BaseSocketTransport):
    MAX_UDP_PACKET_SIZE = 8192
    
    def __init__(self, reactor, sock):
        BaseSocketTransport.__init__(self, reactor, sock)
        self._read_queue = Queue()
        self._write_queue = Queue()

    def sendto(self, host, port, data):
        if len(data) > self.MAX_UDP_PACKET_SIZE:
            raise ValueError("data too long")
        dfr = Deferred()
        self._write_queue.push((dfr, (host, port), data))
        self.reactor.register_write(self)
        return dfr
    
    def recvfrom(self, count = -1):
        dfr = Deferred()
        self._read_queue.push((dfr, count))
        self.reactor.register_read(self)
        return dfr
    
    def on_read(self, hint):
        dfr, count = self._read_queue.pop()
        if hint < count:
            hint = count
        if hint < 0:
            hint = self.MAX_UDP_PACKET_SIZE
        try:
            data, (host, port) = self.sock.recvfrom(hint)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set((host, port, data))
        if not self._read_queue:
            self.reactor.unregister_read(self)

    def on_write(self, hint):
        dfr, addr, data = self._write_queue.pop()
        try:
            count = self.sock.sendto(data, addr)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(count)
        if not self.write_queue:
            self.reactor.unregister_write(self)


class ConnectedUdpTransport(BaseSocketTransport):
    def __init__(self, reactor, sock):
        BaseSocketTransport.__init__(self, reactor, sock)
        self._read_queue = Queue()
        self._write_queue = Queue()
        
    def send(self, data):
        if len(data) > UdpTransport.MAX_UDP_PACKET_SIZE:
            raise ValueError("data too long")
        dfr = Deferred()
        self._write_queue.push((dfr, data))
        self.reactor.register_write(self)
        return dfr
    
    def recv(self, count = -1):
        dfr = Deferred()
        self._read_queue.push((dfr, count))
        self.reactor.register_read(self)
        return dfr
    
    def on_read(self, hint):
        dfr, count = self._read_queue.pop()
        if hint < count:
            hint = count
        if hint < 0:
            hint = UdpTransport.MAX_UDP_PACKET_SIZE
        try:
            data = self.sock.recv(hint)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(data)
        if not self._read_queue:
            self.reactor.unregister_read(self)

    def on_write(self, hint):
        dfr, data = self._write_queue.pop()
        try:
            count = self.sock.send(data)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(count)
        if not self._write_queue:
            self.reactor.unregister_write(self)

#===============================================================================
# SSL
#===============================================================================

class StreamSslTransport(StreamSocketTransport):
    __slots__ = []
    
    def getpeercert(self, binary_form = False):
        return self.fileobj.getpeercert(binary)
    
    def unwrap(self):
        s = self.fileobj.unwrap()
        self.detach()
        return StreamSocketTransport(self.reactor, s)

    def _do_read(self, count):
        try:
            return self.fileobj.recv(count)
        except ssl.SSLError as ex:
            if ex.errno == ssl.SSL_ERROR_WANT_READ:
                raise NeedMoreData
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
    def __init__(self, reactor, sslsock):
        BaseSocketTransport.__init__(self, reactor, sslsock)
        self.connected_dfr = Deferred()
    
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
            trns = StreamSslTransport(self.reactor, self.sock)
            self.detach()
            self.connected_dfr.set(trns)
    
    def on_read(self, hint):
        self.reactor.unregister_read(self)
        self._handshake()
    
    def on_write(self, hint):
        self.reactor.unregister_write(self)
        self._handshake()


class ListeningSslTransport(ListeningSocketTransport):
    def __init__(self, reactor, sock):
        ListeningSocketTransport.__init__(self, reactor, sock, SslHandshakingTransport)
    
    @reactive
    def accept(self):
        handshaking_trns = yield ListeningSocketTransport.accept()
        trns = yield handshaking_trns.handshake()
        rreturn(trns)




