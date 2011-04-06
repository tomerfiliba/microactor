from .base import Subsystem
from microactor.utils import reactive, rreturn
import ssl

from microactor.reactors.posix.transports.sockets import TcpStreamTransport


class SslHandshakeTransport(BaseTransport):
    def __init__(self, reactor, sslsock, dfr):
        BaseTransport.__init__(self, reactor)
        self.sslsock.setblocking(False)
        self.sslsock = sslsock
        self.dfr = dfr
    def close(self):
        BaseTransport.close(self)
        self.sslsock.close()
    def fileno(self):
        return self.sslsock.fileno()
    
    def handshake(self):
        try:
            self.sslsock.do_handshake()
        except ssl.SSLError as ex:
            errno = ex.args[0]
            if errno == ssl.SSL_ERROR_WANT_READ:
                self.reactor.register_read(self)
            elif errno == ssl.SSL_ERROR_WANT_WRITE:
                self.reactor.register_write(self)
            else:
                raise
        else:
            self.dfr.set()
    
    def on_read(self, hint):
        self.reactor.unregister_read(self)
        self.handshake()
    
    def on_write(self, hint):
        self.reactor.unregister_write(self)
        self.handshake()


class SslListeningSocketTransport(ListeningSocketTransport):
    @reactive
    def accept(self):
        conn = yield ListeningSocketTransport.accept(self)
        rreturn conn
        
        self.reactor.register_read(self)
        dfr = Deferred()
        self.accept_queue.push(dfr)
        return dfr


class SslSubsystem(Subsystem):
    NAME = "ssl"
    
    @reactive
    def connect(self, host, port, keyfile = None, certfile = None, 
            ca_certs = None, cert_reqs = ssl.CERT_NONE, ssl_version = ssl.SSLv23):
        conn = yield self.reactor.tcp.connect(host, port)
        sock2 = ssl.wrap_socket(conn.fileobj, keyfile = keyfile, certfile = certfile, 
            ca_certs = ca_certs, cert_reqs = cert_reqs, ssl_version = ssl_version,
            server_side = False, do_handshake_on_connect = False)
        dfr = Deferred()
        trns = SslHandshakeTransport(self.reactor, sock2, dfr)
        yield dfr
        rreturn (TcpStreamTransport(self.reactor, sock2))
    
    @reactive
    def listen(self, port, keyfile, certfile, ca_certs = None, host = "0.0.0.0",
            backlog = 40, cert_reqs = ssl.CERT_NONE, ssl_version = ssl.SSLv3):
        listener = yield self.reactor.tcp.listen(port, host, backlog)




















