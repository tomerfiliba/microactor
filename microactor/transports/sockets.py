import socket
import errno
import sys
from .base import BaseTransport, StreamTransport
from microactor.utils import Deferred
from microactor.lib import Queue


class TcpStreamTransport(StreamTransport):
    def __init__(self, reactor, sock):
        StreamTransport.__init__(self, reactor, sock)
        self.local_info = sock.getsockname()
        self.peer_info = sock.getpeername()
    
    def shutdown(self, mode = "rw"):
        mode2 = {"r" : socket.SHUT_RD, "w" : socket.SHUT_WR, "rw" : socket.SHUT_RDWR}[mode]
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
        self.sock = sock
        self.transport_factory = transport_factory
        self.accept_queue = Queue()
    
    def close(self):
        BaseTransport.close(self)
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
        BaseTransport.close(self)
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


