import socket
from .base import Subsystem
from microactor.utils import reactive, rreturn


class SocketServer(object):
    def __init__(self, reactor, listener):
        self.reactor = reactor
        self.listener = listener
    
    def start(self):
        pass
    
    def close(self):
        pass


class NetSubsystem(Subsystem):
    NAME = "net"
    
    def resolve(self, host):
        return self.reactor.threadpool.call(socket.gethostbyname, host)
    def resolve_ex(self, host):
        return self.reactor.threadpool.call(socket.gethostbyname_ex, host)

    @reactive
    def serve(self, port):
        listener = yield self.listen_tcp(port)
        server = SocketServer(listener)
        rreturn(server)


