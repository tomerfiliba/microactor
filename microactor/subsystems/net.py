import socket
import weakref
from .base import Subsystem
from microactor.utils import reactive, rreturn


class BaseSocketHandler(object):
    __slots__ = ["reactor", "server", "conn"]
    def __init__(self, reactor, server, conn):
        self.reactor = reactor
        self.server = server
        self.conn = conn
    @reactive
    def close(self):
        yield self.conn.close()
        self.server.clients.discard(self)
    @reactive
    def start(self):
        pass

class SocketServer(object):
    def __init__(self, reactor, handler_factory, listener):
        self.reactor = reactor
        self.handler_factory = handler_factory
        self.listener = listener
        self.active = False
        self.clients = set()
    
    @reactive
    def start(self):
        self.active = True
        try:
            while self.active:
                conn = yield self.listener.accept()
                handler = self.handler_factory(self.reactor, weakref.proxy(self), conn)
                self.clients.add(handler)
                self.reactor.call(handler.start)
        except socket.error:
            if not self.active:
                pass # assume it's because listener has closed
            else:
                raise
        for handler in set(self.clients):
            yield handler.close()
    
    @reactive
    def close(self):
        if not self.active:
            return
        self.active = False
        listener = self.listener
        self.listener = None
        listener.close()


class NetSubsystem(Subsystem):
    NAME = "net"
    
    def getaddrinfo(self, hostname, port = None, family = 0, socktype = 0, proto = 0, flags = 0):
        return self.reactor.threadpool.call(socket.getaddrinfo, hostname, port, 
            family, socktype, proto, flags)
    
    @reactive
    def resolve(self, hostname, family = socket.AF_INET):
        res = yield self.getaddrinfo(hostname, family = family)
        print "!!resolve", res
        rreturn(res[0][4][0])

    @reactive
    def serve(self, handler_factory, port, host = "0.0.0.0", backlog = 40):
        listener = yield self.listen_tcp(port, host, backlog)
        server = SocketServer(self.reactor, handler_factory, listener)
        self.reactor.call(server.start)
        rreturn(server)


