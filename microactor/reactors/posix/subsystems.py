import socket
from microactor.subsystems import Subsystem
from .transports import ListeningSocketTransport, ConnectingSocketTransport
from microactor.utils import reactive, rreturn


class NetSubsystem(Subsystem):
    NAME = "net"
    
    def resolve(self, host):
        return self.reactor.threadpool.call(socket.gethostbyname, host)
    def resolve_ex(self, host):
        return self.reactor.threadpool.call(socket.gethostbyname_ex, host)

    @reactive
    def connect_tcp(self, host, port, timeout = None):
        yield self.reactor.started
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        hostaddr = yield self.resolve(host)
        trns = ConnectingSocketTransport(self.reactor, sock, (hostaddr, port))
        trns2 = yield trns.connect(timeout)
        rreturn(trns2)
    
    @reactive
    def listen_tcp(self, port, host = "0.0.0.0", backlog = 40):
        yield self.reactor.started
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        sock.listen(backlog)
        trns = ListeningSocketTransport(self.reactor, sock)
        rreturn(trns)



POSIX_SUBSYSTEMS = [NetSubsystem]
