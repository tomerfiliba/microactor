from .base import Subsystem
from microactor.utils import reactive, rreturn
import ssl


class TcpServer(object):
    def __init__(self, reactor, port, client_handler, bindhost = "0.0.0.0", backlog = 40):
        self.reactor = reactor
        self.port = port
        self.bindhost = bindhost
        self.backlog = backlog
        self.client_handler = client_handler
        self.listener = None
    
    @reactive
    def start(self):
        self.listener = yield self.reactor.net.listen_tcp(self.port, 
            self.bindhost, self.backlog)
        try:
            while True:
                sock = yield self.listener.accept()
                self.reactor.call(self.client_handler, sock)
        except Exception:
            if not self.listener:
                pass # accept() failed because we closed the listener
            else:
                raise

    @reactive
    def close(self):
        if self.listener:
            listener = self.listener
            self.listener = None
            yield listener.close()


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
        sock = conn.fileobj
        
        self.reactor.register_read(self)
        dfr = Deferred()
        self.accept_queue.push(dfr)
        return dfr


class NetSubsystem(Subsystem):
    NAME = "net"
    
    @reactive
    def connect_ssl(self, host, port, keyfile = None, certfile = None, 
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
    def listen_ssl(self, port, keyfile, certfile, ca_certs = None, host = "0.0.0.0",
            backlog = 40, cert_reqs = ssl.CERT_NONE, ssl_version = ssl.SSLv3):
        listener = yield self.reactor.tcp.listen(port, host, backlog)
    
    def serve_tcp(self, port, handler, **kwargs):
        server = TcpServer(self.reactor, port, handler, **kwargs)
        self.reactor.call(server.start)
        return server
    
    @reactive
    def resolve(self, hostname):
        res = yield self.reactor.threading.call(socket.gethostbyname_ex, hostname)
        rreturn(res)
    
    def listen_tcp(self, *args, **kwargs):
        raise NotImplementedError()
    
    def connect_tcp(self, *args, **kwargs):
        raise NotImplementedError()
    
    def open_udp(self, *args, **kwargs):
        raise NotImplementedError()
    
    def connect_udp(self, *args, **kwargs):
        raise NotImplementedError()















