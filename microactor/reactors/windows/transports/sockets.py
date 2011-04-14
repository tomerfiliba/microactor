import socket
from .base import BaseTransport, StreamTransport
from microactor.utils import Deferred, safe_import, reactive
win32file = safe_import("win32file")


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
    
    @reactive
    def close(self):
        try:
            self.shutdown()
        except EnvironmentError:
            pass
        yield StreamTransport.close(self)

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

    def shutdown(self, mode = "rw"):
        mode2 = self._SHUTDOWN_MAP[mode]
        self.fileobj.shutdown(mode2)


class ListeningSocketTransport(BaseTransport):
    def __init__(self, reactor, sock, transport_factory):
        BaseTransport.__init__(self, reactor)
        sock.setblocking(False)
        self.sock = sock
        self._local_addr = None
        self.transport_factory = transport_factory
        self._keepalive = {}
        self._register()

    @property
    def local_addr(self):
        if not self._local_addr:
            self._local_addr = self.sock.getsockname()
        return self._local_addr

    def close(self):
        self.sock.close()
    def fileno(self):
        return self.sock.fileno()
    
    def accept(self):
        def finished(size, overlapped):
            self._keepalive.pop(overlapped)
            self.reactor.call(dfr.set, trns)
        
        dfr = Deferred()
        overlapped = win32file.OVERLAPPED()
        overlapped.object = finished
        self._keepalive[overlapped] = finished
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        trns = self.transport_factory(self.reactor, sock)
        fd = trns.fileno()
        buffer = win32file.AllocateReadBuffer(win32file.CalculateSocketEndPointSize(fd))
        win32file.AcceptEx(self.fileno(), fd, buffer, overlapped)
        
        return dfr


class UdpTransport(BaseTransport):
    def __init__(self, reactor, sock):
        BaseTransport.__init__(self, reactor)
        sock.setblocking(False)
        self._sock = sock
        self._register()

    def close(self):
        self._sock.close()
    def fileno(self):
        return self._sock.fileno()
    
    def sendto(self, host, port, data):
        raise NotImplementedError()
    
    def recvfrom(self, count = -1):
        raise NotImplementedError()




