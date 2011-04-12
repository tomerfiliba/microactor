from .base import Subsystem
from microactor.utils import reactive, rreturn, Deferred
import ssl


class TcpServer(object):
    def __init__(self, reactor, port, client_handler, bindhost = "0.0.0.0", backlog = 40):
        self.reactor = reactor
        self.port = port
        self.bindhost = bindhost
        self.backlog = backlog
        self.client_handler = client_handler
        self.listener = None
        self.active = False
        self.running_dfr = Deferred()
        self.closed_dfr = Deferred()
    
    @reactive
    def start(self):
        self.listener = yield self.reactor.net.listen_tcp(self.port, 
            self.bindhost, self.backlog)
        self.active = True
        self.bindhost, self.port = self.listener.local_addr
        self.running_dfr.set()
        try:
            while self.active:
                sock = yield self.listener.accept()
                self.reactor.call(self.client_handler, sock)
        except Exception as ex:
            if not self.accept:
                # accept() failed because we closed the listener
                self.closed_dfr.set()
            else:
                self.closed_dfr.throw(ex)
        finally:
            self.listener.close()

    @reactive
    def close(self):
        if self.active:
            self.active = False
            yield self.listener.close()
        yield self.closed_dfr


class NetSubsystem(Subsystem):
    NAME = "net"
    
    @reactive
    def resolve(self, hostname):
        res = yield self.reactor.threading.call(socket.gethostbyname_ex, hostname)
        rreturn(res)
    
    def listen_tcp(self, *args, **kwargs):
        raise NotImplementedError()
    
    def connect_tcp(self, *args, **kwargs):
        raise NotImplementedError()

    def listen_ssl(self, *args, **kwargs):
        raise NotImplementedError()
    
    def connect_ssl(self, *args, **kwargs):
        raise NotImplementedError()
    
    def open_udp(self, *args, **kwargs):
        raise NotImplementedError()
    
    def connect_udp(self, *args, **kwargs):
        raise NotImplementedError()

    @reactive
    def serve_tcp(self, port, handler, **kwargs):
        server = TcpServer(self.reactor, port, handler, **kwargs)
        self.reactor.call(server.start)
        yield server.running_dfr
        rreturn(server)














