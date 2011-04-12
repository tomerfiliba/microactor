import socket
import errno
import sys
from .base import BaseTransport, StreamTransport
from microactor.utils.deferred import Deferred
from microactor.utils.colls import Queue


class TcpStreamTransport(StreamTransport):
    __slots__ = ["local_addr", "peer_addr"]
    _SHUTDOWN_MAP = {
        "r" : socket.SHUT_RD, 
        "w" : socket.SHUT_WR, 
        "rw" : socket.SHUT_RDWR
    }
    
    def __init__(self, reactor, sock):
        StreamTransport.__init__(self, reactor, sock)
        sock.setblocking(False)
        self.local_addr = sock.getsockname()
        self.peer_addr = sock.getpeername()
    
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


class ListeningSocketTransport(BaseTransport):
    def __init__(self, reactor, sock, transport_factory):
        BaseTransport.__init__(self, reactor)
        sock.setblocking(False)
        self.local_addr = sock.getsockname()
        self.sock = sock
        self.transport_factory = transport_factory
        self.accept_queue = Queue()
    
    def close(self):
        self._unregister()
        self.sock.close()
    def fileno(self):
        return self.sock.fileno()
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


class ConnectingSocketTransport(BaseTransport):
    def __init__(self, reactor, sock, addr, deferred, transport_factory):
        BaseTransport.__init__(self, reactor)
        self.sock = sock
        self.addr = addr
        self.deferred = deferred
        self.connected = False
        self.transport_factory = transport_factory
    
    def close(self):
        self._unregister()
        self.sock.close()
    def fileno(self):
        return self.sock.fileno()
    
    def connect(self, timeout):
        if timeout is not None:
            self.reactor.call_after(timeout, self._cancel)
        self.reactor.register_write(self)
        self.sock.setblocking(False)
        self._attempt_connect()
    
    def _attempt_connect(self):
        if self.deferred.is_set():
            self._unregister()
            return
        err = self.sock.connect_ex(self.addr)
        if err in (errno.EINPROGRESS, errno.EALREADY, errno.EWOULDBLOCK):
            return
        if err == errno.EINVAL and sys.platform == "win32":
            return
        
        self.reactor.unregister_write(self)
        if err in (0, errno.EISCONN):
            trns = self.transport_factory(self.reactor, self.sock)
            self.deferred.set(trns)
        else:
            self.deferred.throw(socket.error(err, errno.errorcode[err]))
    
    def on_write(self, hint):
        self._attempt_connect()
    
    def _cancel(self, job):
        if self.deferred.is_set():
            return
        self.close()
        self.deferred.throw(socket.timeout("connection timed out"))


class UdpTransport(BaseTransport):
    __slots__ = ["_sock", "_read_queue", "_write_queue"]
    MAX_UDP_PACKET_SIZE = 8192
    
    def __init__(self, reactor, sock):
        BaseTransport.__init__(self, reactor)
        sock.setblocking(False)
        self._sock = sock
        self._read_queue = Queue()
        self._write_queue = Queue()
        
    def close(self):
        self._unregister()
        self._sock.close()
    def fileno(self):
        return self._sock.fileno()
    
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
            data, (host, port) = self._sock.recvfrom(hint)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set((host, port, data))
        if not self._read_queue:
            self.reactor.unregister_read(self)

    def on_write(self, hint):
        dfr, addr, data = self._write_queue.pop()
        try:
            count = self._sock.sendto(data, addr)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(count)
        if not self.write_queue:
            self.reactor.unregister_write(self)


class ConnectedUdpTransport(BaseTransport):
    __slots__ = ["_sock", "_read_queue", "_write_queue"]

    def __init__(self, reactor, sock):
        BaseTransport.__init__(self, reactor)
        self._sock = sock
        self._read_queue = Queue()
        self._write_queue = Queue()
        
    def close(self):
        self._unregister()
        self._sock.close()
    def fileno(self):
        return self._sock.fileno()
    
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
            data = self._sock.recv(hint)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(data)
        if not self._read_queue:
            self.reactor.unregister_read(self)

    def on_write(self, hint):
        dfr, data = self._write_queue.pop()
        try:
            count = self._sock.send(data)
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(count)
        if not self._write_queue:
            self.reactor.unregister_write(self)


class SslHandshakeTransport(BaseTransport):
    def __init__(self, reactor, sslsock, dfr):
        BaseTransport.__init__(self, reactor)
        self.sslsock.setblocking(False)
        self.sslsock = sslsock
        self.dfr = dfr
    def close(self):
        BaseTransport.close(self)
        self.sslsock.close()
    def fileno(self):
        return self.sslsock.fileno()
    
    def handshake(self):
        try:
            self.sslsock.do_handshake()
        except ssl.SSLError as ex:
            errno = ex.args[0]
            if errno == ssl.SSL_ERROR_WANT_READ:
                self.reactor.register_read(self)
            elif errno == ssl.SSL_ERROR_WANT_WRITE:
                self.reactor.register_write(self)
            else:
                raise
        else:
            self.dfr.set()
    
    def on_read(self, hint):
        self.reactor.unregister_read(self)
        self.handshake()
    
    def on_write(self, hint):
        self.reactor.unregister_write(self)
        self.handshake()


class SslListeningSocketTransport(ListeningSocketTransport):
    def accept(self):
        conn = yield ListeningSocketTransport.accept(self)
        sock = conn.fileobj
        
        self.reactor.register_read(self)
        dfr = Deferred()
        self.accept_queue.push(dfr)
        rreturn(dfr)












