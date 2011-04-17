import socket
from microactor.subsystems import Subsystem
from microactor.utils import ReactorDeferred, reactive, rreturn, safe_import
from .transports import SocketStreamTransport, ListeningSocketTransport
win32file = safe_import("win32file")


class NetSubsystem(Subsystem):
    NAME = "net"

    def resolve(self, host):
        return self.reactor.threadpool.call(socket.gethostbyname, host)
    def resolve_ex(self, host):
        return self.reactor.threadpool.call(socket.gethostbyname_ex, host)
    
    @reactive
    def connect_tcp(self, host, port, timeout = None):
        def connect_finished(size, overlapped):
            dfr.set(trns)

        yield self.reactor.started
        hostaddr = yield self.resolve(host)
        dfr = ReactorDeferred(self.reactor)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.bind(('0.0.0.0', 0)) # ConnectEx requires the socket to be bound
        # this is required here to register the new socket with its IOCP
        trns = SocketStreamTransport(self.reactor, sock)
        overlapped = self.reactor._get_overlapped(connect_finished)
        try:
            win32file.ConnectEx(sock.fileno(), (hostaddr, port), overlapped)
        except Exception:
            self.reactor._discard_overlapped(overlapped)
            raise
        yield trns
        rreturn(trns)
    
    @reactive
    def listen_tcp(self, port, host = "0.0.0.0", backlog = 40):
        yield self.reactor.started
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.bind((host, port))
        sock.listen(backlog)
        rreturn(ListeningSocketTransport(self.reactor, sock))


IOCP_SUBSYSTEMS = [NetSubsystem]
