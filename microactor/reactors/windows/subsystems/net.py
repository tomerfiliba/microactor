import socket
from microactor.subsystems.net import NetSubsystem
from microactor.utils import Deferred, safe_import, reactive, rreturn
from ..transports import (ListeningSocketTransport, TcpStreamTransport, 
    UdpTransport)
win32file = safe_import("win32file")


class IocpNetSubsystem(NetSubsystem):
    def connect_tcp(self, host, port):
        def finished(size, overlapped):
            self._keepalive.pop(overlapped)
            self.reactor.call(dfr.set)
        
        def do_connect(is_exc, value):
            if is_exc:
                dfr.throw(value)
                return
            win32file.ConnectEx(sock.fileno(), (value, port), overlapped)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', 0)) # ConnectEx requires sock to be bound
        overlapped = win32file.OVERLAPPED()
        overlapped.object = finished
        self._keepalive[overlapped] = finished
        dfr = Deferred()
        addr_dfr = self.resolve(host)
        addr_dfr.register(do_connect)
        return dfr
    
    def listen_tcp(self, port, host = "0.0.0.0", backlog = 40):
        def do_listen():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            sock.bind((host, port))
            sock.listen(backlog)
            dfr.set(ListeningSocketTransport(self.reactor, sock, TcpStreamTransport))
        dfr = Deferred()
        self.reactor.call(do_listen)
        return dfr

    @classmethod
    def _open_udp_sock(cls, host, port, broadcast):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.bind((host, port))
        if broadcast:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        return sock

    def open_udp(self, port = 0, host = "0.0.0.0", broadcast = False):
        def do_open():
            try:
                sock = self._open_udp_sock(host, port, broadcast)
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(UdpTransport(self.reactor, sock))
        
        dfr = Deferred()
        self.reactor.call(do_open)
        return dfr
    



