import socket
from microactor.subsystems.net import NetSubsystem
from microactor.utils import Deferred, safe_import, reactive, rreturn
from ..transports import (ListeningSocketTransport, StreamSocketTransport, 
    UdpTransport)
win32file = safe_import("win32file")


class IocpNetSubsystem(NetSubsystem):
    def _init(self):
        self._keepalive = {}
    
    @reactive
    def connect_tcp(self, host, port):
        yield self.reactor.started
        addr = yield self.resolve(host)
        trns_dfr = Deferred()
        
        print "connect_tcp: trns_dfr =", trns_dfr
        
        def finished(size, overlapped):
            print "connect_tcp: ConnectEx finished"
            self._keepalive.pop(overlapped)
            self.reactor.call(trns_dfr.set, StreamSocketTransport(self.reactor, sock))

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', 0)) # ConnectEx requires the socket to be bound
        overlapped = win32file.OVERLAPPED()
        overlapped.object = finished
        self._keepalive[overlapped] = finished

        print "connect_tcp: calling ConnectEx"

        win32file.ConnectEx(sock.fileno(), (addr, port), overlapped)
        print "connect_tcp: waiting for ConnectEx"
        trns = yield trns_dfr
        print "connect_tcp: done", trns
        rreturn(trns)
    
    @reactive
    def listen_tcp(self, port, host = "0.0.0.0", backlog = 40):
        yield self.reactor.started
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.bind((host, port))
        sock.listen(backlog)
        rreturn(ListeningSocketTransport(self.reactor, sock, StreamSocketTransport))

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
                self.reactor.call(dfr.throw, ex)
            else:
                self.reactor.call(dfr.set, UdpTransport(self.reactor, sock))
        
        dfr = Deferred()
        self.reactor.call(do_open)
        return dfr
    



