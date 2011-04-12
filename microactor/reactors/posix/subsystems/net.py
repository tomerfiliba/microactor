import sys
import socket
from microactor.subsystems.net import NetSubsystem
from microactor.utils import Deferred, reactive, rreturn
from ..transports import (ConnectingSocketTransport, ListeningSocketTransport, 
    TcpStreamTransport, UdpTransport, ConnectedUdpTransport)


class PosixNetSubsystem(NetSubsystem):
    def connect_tcp(self, host, port, timeout = None):
        dfr = Deferred()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        trns = ConnectingSocketTransport(self.reactor, sock, (host, port), dfr, 
            TcpStreamTransport)
        self.reactor.call(trns.connect, timeout)
        return dfr
    
    def listen_tcp(self, port, host = "0.0.0.0", backlog = 40):
        def do_listen():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            if sys.platform != "win32":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
        if sys.platform != "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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

    def connect_udp(self, host, port):
        def do_open():
            try:
                sock = self._open_udp_sock("0.0.0.0", 0, False)
                sock.connect((host, port))
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(ConnectedUdpTransport(self.reactor, sock))
        
        dfr = Deferred()
        self.reactor.call(do_open)
        return dfr

    @reactive
    def resolve(self, hostname):
        res = yield self.reactor.threading.call(socket.gethostbyname_ex, hostname)
        rreturn(res)




