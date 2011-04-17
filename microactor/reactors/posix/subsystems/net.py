import sys
import socket
import ssl
from microactor.subsystems.net import NetSubsystem
from microactor.utils import Deferred, reactive, rreturn
from ..transports import (ConnectingSocketTransport, ListeningSocketTransport, 
    StreamSocketTransport, UdpTransport, ConnectedUdpTransport, 
    SslHandshakingTransport, ListeningSslTransport)


class PosixNetSubsystem(NetSubsystem):
    
    @reactive
    def connect_tcp(self, host, port, timeout = None):
        yield self.reactor.started
        addr = yield self.resolve(host)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        trns = ConnectingSocketTransport(self.reactor, sock, (addr, port))
        yield trns.connect(timeout)
        rreturn(StreamSocketTransport(self.reactor, sock))
    
    @reactive
    def listen_tcp(self, port, host = "0.0.0.0", backlog = 40):
        yield self.reactor.started
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        if sys.platform != "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(backlog)
        rreturn(ListeningSocketTransport(self.reactor, sock, StreamSocketTransport))

    @classmethod
    def _open_udp_sock(cls, host, port, broadcast):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        if sys.platform != "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        if broadcast:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        return sock
    
    def open_udp(self, port = 0, host = "0.0.0.0", broadcast = False):
        def do_open():
            try:
                sock = self._open_udp_sock(host, port, broadcast)
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(UdpTransport(self.reactor, sock))
        
        dfr = Deferred(self.reactor)
        self.reactor.call(do_open)
        return dfr

    def connect_udp(self, host, port):
        def do_open():
            try:
                sock = self._open_udp_sock("0.0.0.0", 0, False)
                sock.connect((host, port))
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(ConnectedUdpTransport(self.reactor, sock))
        
        dfr = Deferred(self.reactor)
        self.reactor.call(do_open)
        return dfr

    @reactive
    def connect_ssl(self, host, port, timeout = None, keyfile = None, 
            certfile = None, ca_certs = None, cert_reqs = ssl.CERT_NONE, 
            ssl_version = ssl.PROTOCOL_SSLv23):
        
        trns = yield self.connect_tcp(host, port, timeout)
        ssl_trns = yield self.wrap_ssl_client(trns, keyfile = keyfile, certfile = certfile,
            ca_certs = ca_certs, cert_reqs = cert_reqs, ssl_version = ssl_version)
        rreturn(ssl_trns)
    
    @reactive
    def wrap_ssl_client(self, transport, keyfile = None, certfile = None, ca_certs = None,
            cert_reqs = ssl.CERT_NONE, ssl_version = ssl.PROTOCOL_SSLv23):
        
        sslsock = ssl.wrap_socket(transport.fileobj, keyfile = keyfile, 
            certfile = certfile, ca_certs = ca_certs, cert_reqs = cert_reqs,
            ssl_version = ssl_version, server_side = False, 
            do_handshake_on_connect = False)
        transport.detach()
        
        handshaking_trns = SslHandshakingTransport(self.reactor, sslsock)
        connected_trns = yield handshaking_trns.handshake()
        rreturn(connected_trns)
    
    @reactive
    def wrap_ssl_server(self, listener, keyfile, certfile, ca_certs = None, 
            cert_reqs = ssl.CERT_NONE, ssl_version = ssl.PROTOCOL_SSLv23):
        sock = listener.sock
        listener.detach()
        sslsock = ssl.wrap_socket(sock, keyfile = keyfile, 
            certfile = certfile, ca_certs = ca_certs, cert_reqs = cert_reqs,
            ssl_version = ssl_version, server_side = True, 
            do_handshake_on_connect = False)
        
        trns = ListeningSslTransport(self.reactor, sslsock)
        rreturn(trns)
    
    @reactive
    def listen_ssl(self, port, keyfile, certfile, host = "0.0.0.0", backlog = 40,
            ca_certs = None, cert_reqs = ssl.CERT_NONE, ssl_version = ssl.PROTOCOL_SSLv23):
        
        listener = yield self.listen_tcp(port, host, backlog)
        ssl_listener = self.wrap_ssl_server(listener, keyfile, certfile, 
            ca_certs = ca_certs, cert_reqs = cert_reqs, ssl_version = ssl_version)
        rreturn(ssl_listener)









