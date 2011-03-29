import sys
from .base import Subsystem
from microactor.utils.reactive import reactive, Deferred, rreturn, timed, TimedOut
import itertools
import socket
from struct import Struct


UBI16 = Struct("!H")

class DnsSubsystem(Subsystem):
    NAME = "dns"
    DEPENDENCIES = ["udp"]
    DEFAULT_NAME_SERVER = "8.8.8.8"
    UDP_PORT = 53
    
    def _init(self):
        self.id_generator = itertools.count()
        self.requests = {}
        self.nameservers = []
        self.sock = None
        self.pending_requests = {}
        self.reactor.call(self.requests_collector)
    
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
                    ips.append((tokens[1], self.UDP_PORT))
        return ips
    
    @reactive
    def _windows_get_nameservers(self):
        proc = yield self.reactor.proc.run(["ipconfig", "/all"])
        yield proc.wait()
        data = yield proc.stdin.read()
        ips = []
        lines = data.splitlines()
        while lines:
            line = lines.pop(0).strip() 
            if line.startswith("DNS Servers"):
                ip = line.split(":", 1)[1]
                if ":" not in ip: # skip ipv6
                    ips.append((ip, self.UDP_PORT))
                while lines:
                    line = lines[0].strip()
                    if ":" not in line:
                        lines.pop(0)
                        ips.append((line, self.UDP_PORT))
        return ips
    
    @reactive
    def requests_collector(self):
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
        tid = self.id_generator.next() % 65536
        req = "%s\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03%s\x00\x00\x01\x00\x01" % (UBI16.pack(tid), hostname)
        
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















