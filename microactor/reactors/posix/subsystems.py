import sys
import socket
from microactor.subsystems import Subsystem
from microactor.utils import reactive, rreturn, safe_import
from .transports import (ListeningSocketTransport, ConnectingSocketTransport, 
    SslHandshakingTransport, SslListeninglSocketTransport, DatagramSocketTransport)
ssl = safe_import("ssl")


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
        if sys.platform != "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        sock.bind((host, port))
        sock.listen(backlog)
        trns = ListeningSocketTransport(self.reactor, sock)
        rreturn(trns)
    
    @reactive
    def wrap_ssl_client(self, transport, keyfile = None, certfile = None, 
            ca_certs = None, cert_reqs = None, ssl_version = None):
        yield self.reactor.started
        if ssl_version is None:
            ssl_version = ssl.PROTOCOL_SSLv23
        if cert_reqs is None:
            cert_reqs = ssl.CERT_NONE
        sslsock = ssl.wrap_socket(transport.fileobj, keyfile = keyfile, 
            certfile = certfile, ca_certs = ca_certs, cert_reqs = cert_reqs, 
            ssl_version = ssl_version, server_side = False, do_handshake_on_connect = False, 
            suppress_ragged_eofs = True)
        transport.detach()
        handshaker = SslHandshakingTransport(self.reactor, sslsock)
        ssltrns = yield handshaker.handshake()
        rreturn(ssltrns)
    
    @reactive
    def connect_ssl(self, host, port, timeout = None, keyfile = None, 
            certfile = None, ca_certs = None, cert_reqs = None, ssl_version = None):
        trns = yield self.connect_tcp(host, port, timeout)
        ssltrns = yield self.wrap_ssl_client(trns, keyfile = keyfile, 
            certfile = certfile, cert_reqs = cert_reqs, ca_certs = ca_certs,
            ssl_version = ssl_version)
        rreturn(ssltrns)

    @reactive
    def wrap_ssl_server(self, transport, keyfile, certfile, ca_certs = None, 
            cert_reqs = None, ssl_version = None):
        yield self.reactor.started
        if ssl_version is None:
            ssl_version = ssl.PROTOCOL_SSLv23
        if cert_reqs is None:
            cert_reqs = ssl.CERT_NONE
        sslsock = ssl.wrap_socket(transport.fileobj, keyfile = keyfile, 
            certfile = certfile, ca_certs = ca_certs, cert_reqs = cert_reqs, 
            ssl_version = ssl_version, server_side = True, do_handshake_on_connect = False, 
            suppress_ragged_eofs = True)
        transport.detach()
        ssltrns = SslListeninglSocketTransport(self.reactor, sslsock)
        rreturn(ssltrns)
    
    @reactive
    def listen_ssl(self, port, host = "0.0.0.0", backlog = 40, keyfile = None, 
            certfile = None, ca_certs = None, cert_reqs = None, ssl_version = None):
        listener = yield self.listen_tcp(port, host, backlog)
        ssl_listener = self.wrap_ssl_server(listener, keyfile, certfile, 
            ca_certs = ca_certs, cert_reqs = cert_reqs, ssl_version = ssl_version)
        rreturn(ssl_listener)

    @classmethod
    def _open_udp_sock(cls, host, port, broadcast):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        if sys.platform != "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        sock.bind((host, port))
        if broadcast:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        return sock
    
    @reactive
    def open_udp(self, port, host = "0.0.0.0", broadcast = False):
        yield self.reactor.started
        sock = self._open_udp_sock(host, port, broadcast)
        trns = DatagramSocketTransport(self.reactor, sock)
        rreturn(trns)
        
    @reactive
    def connect_udp(self, host, port, broadcast = False):
        yield self.reactor.started
        sock = self._open_udp_sock("0.0.0.0", 0, broadcast)
        hostaddr = yield self.resolve(host)
        trns = ConnectingSocketTransport(self.reactor, sock, (hostaddr, port))
        trns2 = yield trns.connect()
        rreturn(trns2)



POSIX_SUBSYSTEMS = [NetSubsystem]



