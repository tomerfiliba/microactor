from microactor.subsystems.base import Subsystem
from microactor.utils import reactive, rreturn
from microactor.utils import BufferedTransport, BoundTransport


class CaseInsensitiveDict(dict):
    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)
    def __setitem__(self, name, value):
        return dict.__setitem__(self, name.lower(), value)
    def update(self, *args, **kwargs):
        d = dict(*args, **kwargs)
        for k, v in d.items():
            self[k] = v

class HttpRequest(object):
    def __init__(self, conn, hostinfo, path):
        self.conn = conn
        self.proto = proto
        self.hostinfo = hostinfo
        self.options = CaseInsensitiveDict()
        self["User-Agent"] = "Mozilla/5.0"
        self["Connection"] = "keep-alive"
        self["Accept"] = "application/xml,application/xhtml+xml,text/html,text/plain,*/*"
        self["Accept-Charset"] = "utf-8"
        self["Accept-Encoding"] = "gzip,deflate,sdch"
        self["Host"] = self.hostinfo
    
    @reactive
    def close(self):
        yield self.conn.close()
    
    @reactive
    def _fetch_response(self):
        header = yield self.conn.read_until("\r\n\r\n")
        lines = header.splitlines()
        proto, code, message = lines.pop(0).split()
        headers = {istr(k) : v for k, v in (l.split(":", 1) for l in lines)}
        if "content-length" in headers:
            conn2 = BoundTransport(self.conn, int(headers["content-length"]), None)
        rreturn(HttpResponse(proto, code, message, headers, conn2))
    
    @reactive
    def get(self, path, options = None):
        if not options:
            opts = options
        else:
            opts = self.options.copy()
            opts.update((istr(k), v) for k, v in options)
        
        yield self.conn.write("GET %s HTTP/1.1\r\n" % (path,))
        for k, v in opts.items():
            yield self.conn.write("%s: %s\r\n" % (k, v))
        yield self.conn.write("\r\n")
        yield self.conn.flush()
        yield self._fetch_response()


class HttpRequestChain(object):
    def __init__(self, conn, proto, hostinfo):
        self.conn = conn
        self.proto = proto
        self.hostinfo = hostinfo
        self.options = {}
        self["User-Agent"] = "Mozilla/5.0"
        self["Connection"] = "keep-alive"
        self["Accept"] = "application/xml,application/xhtml+xml,text/html,text/plain,*/*"
        self["Accept-Charset"] = "utf-8"
        self["Accept-Encoding"] = "gzip,deflate,sdch"
        self["Host"] = self.hostinfo

    def __getitem__(self, key):
        return self.options[istr(key)]
    def __delitem__(self, key):
        del self.options[istr(key)]
    def __setitem__(self, key, value):
        self.options[istr(key)] = value
    
    @reactive
    @classmethod
    def from_url(cls, reactor, url):
        if "://" in url:
            proto, url = url.split("://", 1)
        else:
            proto = "http"
        if "/" in url:
            hostinfo, url = url.split("/", 1)
        else:
            hostinfo = url
            url = "/"
        if ":" in hostinfo:
            host, port = hostinfo.split(":", 1)
        else:
            host = hostinfo
            port = 80
        path = url
        conn = yield reactor.tcp.connect(host, port)
        conn2 = BufferedTransport(conn)
        inst = cls(conn2, proto, hostinfo)
        rreturn((inst, path))
    



class HttpSubsystem(Subsystem):
    NAME = "http"
    
    def _init(self):
        self._sessions = {}
    
    @classmethod
    def _parse_url(cls, url):
        if "://" in url:
            scheme, url = url.split("://", 1)
        else:
            scheme = "http"
        if "/" in url:
            hostinfo, url = url.split("/", 1)
        else:
            hostinfo = url
        if ":" in hostinfo:
            host, port = hostinfo.split(":", 1)
        else:
            host = hostinfo
            port = 80
        path = url.strip()
        if not path:
            path = "/"
        return scheme, hostinfo, host, port, path
    
    @reactive
    def get(self, url, options = None):
        scheme, hostinfo, host, port, path = self._parse_url(url)
        key = (scheme, hostinfo)
        if key not in self._sessions:
            self._sessions[key] = yield self.reactor.tcp.connect(host, port)
        conn = self._sessions[key]
        rreturn(HttpRequest(conn, hostinfo, path, options))
            





