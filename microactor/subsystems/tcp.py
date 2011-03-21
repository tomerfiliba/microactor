import sys
import socket
from microactor.subsystems.base import Subsystem
from microactor.utils import Deferred
from microactor.transports.sockets import (ConnectingSocketTransport,
    ListeningSocketTransport, TcpStreamTransport)


class TcpSubsystem(Subsystem):
    NAME = "tcp"
    
    def connect(self, host, port, timeout = None):
        dfr = Deferred()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        trns = ConnectingSocketTransport(self.reactor, sock, (host, port), dfr, 
            TcpStreamTransport)
        self.reactor.call(trns.connect, timeout)
        return dfr
    
    def listen(self, port, host = "0.0.0.0", backlog = 10):
        def do_listen():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            sock.bind((host, port))
            if sys.platform != "win32":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.listen(backlog)
            dfr.set(ListeningSocketTransport(self.reactor, sock, TcpStreamTransport))
        dfr = Deferred()
        self.reactor.call(do_listen)
        return dfr



