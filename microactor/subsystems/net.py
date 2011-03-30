import sys
import socket
import itertools
from struct import Struct
from .base import Subsystem
from microactor.utils import Deferred, reactive, rreturn
from microactor.transports.sockets import (ConnectingSocketTransport,
    ListeningSocketTransport, TcpStreamTransport, UdpTransport,
    ConnectedUdpTransport)


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
            if sys.platform != "win32":
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.listen(backlog)
            dfr.set(ListeningSocketTransport(self.reactor, sock, TcpStreamTransport))
        dfr = Deferred()
        self.reactor.call(do_listen)
        return dfr


class UdpSubsystem(Subsystem):
    NAME = "udp"
    
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
    
    def open(self, port = 0, host = "0.0.0.0", broadcast = False):
        def do_open():
            try:
                sock = self._open_udp_sock(host, port, broadcast)
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(UdpTransport(self.reactor, sock))
        
        dfr = Deferred()
        self.reactor.call(do_open)
        return dfr

    def connect(self, host, port):
        def do_open():
            sock = self._open_udp_sock("0.0.0.0", 0, False)
            sock.connect((host, port))
            dfr.set(ConnectedUdpTransport(self.reactor, sock))
        
        dfr = Deferred()
        self.reactor.call(do_open)
        return dfr


class DnsSubsystem(Subsystem):
    NAME = "dns"
    DEPENDENCIES = ["udp", "proc"]
    DEFAULT_NAME_SERVER = "8.8.8.8"
    DNS_PORT = 53
    UBI16 = Struct("!H")
    
    def _init(self):
        self.id_generator = itertools.count()
        self.requests = {}
        self.nameservers = []
        self.sock = None
        self.pending_requests = {}
        self._collector_installed = False
    
    def _install_collector(self):
        if self._collector_installed:
            return
        self.reactor.call(self._requests_collector)
        self._collector_installed = True
    
    @reactive
    def _get_nameservers(self):
        if sys.platform == "win32":
            self.nameservers = yield self._windows_get_nameservers
        else:
            self.nameservers = yield self._unix_get_nameservers
        self.nameservers.append(self.DEFAULT_NAME_SERVER)
        # http://www.cyberciti.biz/faq/how-to-find-out-what-my-dns-servers-address-is/

    @reactive
    def _unix_get_nameservers(self):
        ips = []
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                tokens = line.strip().split()
                if tokens[0] == "nameserver":
                    ips.append((tokens[1], self.DNS_PORT))
        rreturn(ips)
    
    @reactive
    def _windows_get_nameservers(self):
        _, stdout, _ = yield self.reactor.proc.run(["ipconfig", "/all"])
        ips = []
        lines = stdout.splitlines()
        while lines:
            line = lines.pop(0).strip() 
            if line.startswith("DNS Servers"):
                ip = line.split(":", 1)[1]
                if ":" not in ip: # skip ipv6
                    ips.append((ip, self.DNS_PORT))
                while lines:
                    line = lines[0].strip()
                    if ":" not in line:
                        lines.pop(0)
                        ips.append((line, self.DNS_PORT))
        rreturn(ips)
    
    @reactive
    def _requests_collector(self):
        yield self._get_nameservers()
        self.sock = yield self.reactor.udp.open()
        while True:
            _, _, data = yield self.sock.recvfrom()
            resp = self._parse_response(data)
            if resp.tid not in self.pending_requests:
                continue
            dfr = self.pending_requests.pop(resp.tid)
            dfr.set(resp)
    
    @reactive
    def query(self, hostname):
        self._install_collector()
        tid = self.id_generator.next() % 65536
        req = "%s\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03%s\x00\x00\x01\x00\x01" % (self.UBI16.pack(tid), hostname)
        
        for ns, port in self.nameservers:
            dfr = Deferred()
            self.pending_requests[tid] = dfr
            yield self.sock.sendto(ns, port, req)
            try:
                resp = yield timed(3, dfr)
            except TimedOut:
                self.pending_requests.pop(tid, None)
                continue
            if resp.ok:
                rreturn(resp.ipaddr)
        raise socket.gaierror("could not resolve host")
    
    @reactive
    def resolve(self, hostname):
        res = yield self.reactor.threading.call(socket.gethostbyname_ex, hostname)
        rreturn(res)
        



