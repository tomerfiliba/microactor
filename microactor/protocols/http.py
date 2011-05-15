from microactor.utils import reactive
import itertools
from microactor.utils.transports import BoundTransport


class HttpError(Exception):
    def __init__(self, code, text):
        self.code = code
        self.text = text

class HttpHeaders(object):
    def __init__(self, *args, **kwargs):
        self._items = {}
        self._counter = itertools.count()
        self.update(*args, **kwargs)
    
    @classmethod
    def from_text(cls, text):
        return cls.from_lines(text.splitlines())
    
    @classmethod
    def from_lines(cls, lines):
        inst = cls()
        for line in lines:
            if not line.strip():
                continue
            k, v = line.split(":", 1)
            if "," in v:
                inst[k.strip()] = [item.strip() for item in v.split(",")]
            else:
                inst[k.strip()] = v.strip()
        return inst
    
    def to_text(self):
        lines = []
        for k, v in self.items():
            if isinstance(v, (list, tuple)):
                v = ",".join(v)
            lines.append("%s: %s" % (k, v))
        return b"\r\n".join(lines) + "\r\n\r\n"

    def __repr__(self):
        return "{" + ", ".join("%s : %r" % (k, v) for k, v in self.items()) + "}"
    def __contains__(self, name):
        return name.lower() in self._items
    def __len__(self):
        return len(self._items)
    def __delitem__(self, name):
        del self._items[name.lower()]
    def __getitem__(self, name):
        return self._items[name.lower()][2]
    def __setitem__(self, name, value):
        k = name.lower()
        if k not in self._items:
            ordinal = self._counter.next()
        else:
            ordinal = self._items[k][0]
        self._items[k] = (ordinal, name, value)

    def clear(self):
        self._items.clear()
    def copy(self):
        other = HttpHeaders()
        other._items.update(self._items())
        cnt = int(str(self._counter)[6:-1])
        other._counter = itertools.count(cnt)
        return other
    def keys(self):
        return (k for k, v in self.items())
    def values(self):
        return (v for k, v in self.items())
    def items(self):
        return ((k, v) for _, k, v in sorted(self._items.values()))
    def update(self, _obj = NotImplemented, **kwargs):
        if _obj is not NotImplemented:
            for k, v in _obj.items():
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v
    def pop(self, name, *default):
        return self._items.pop(name, *default)


class HttpRequest(object):
    pass

class HttpResponse(object):
    DEFAULT_MESSAGES = {
        100 : 'Continue',
        101 : 'Switching Protocols',
        102 : 'Processing',
        122 : 'Request-URI too long',
        200 : 'OK',
        201 : 'Created',
        202 : 'Accepted',
        203 : 'Non-Authoritative Information ',
        204 : 'No Content',
        205 : 'Reset Content',
        206 : 'Partial Content',
        300 : 'Multiple Choices',
        301 : 'Moved Permanently',
        302 : 'Found',
        303 : 'See Other',
        304 : 'Not Modified',
        305 : 'Use Proxy',
        306 : 'Switch Proxy',
        307 : 'Temporary Redirect',
        400 : 'Bad Request',
        401 : 'Unauthorized',
        402 : 'Payment Required',
        403 : 'Forbidden',
        404 : 'Not Found',
        405 : 'Method Not Allowed',
        406 : 'Not Acceptable',
        407 : 'Proxy Authentication Required',
        408 : 'Request Timeout',
        409 : 'Conflict',
        410 : 'Gone',
        411 : 'Length Required',
        412 : 'Precondition Failed',
        413 : 'Request Entity Too Large',
        414 : 'Request-URI Too Long',
        415 : 'Unsupported Media Type',
        416 : 'Requested Range Not Satisfiable',
        417 : 'Expectation Failed',
        418 : "I'm a teapot",
        426 : 'Upgrade Required',
        444 : 'No Response',
        449 : 'Retry With',
        450 : 'Blocked by Windows Parental Controls',
        499 : 'Client Closed Request',
        500 : 'Internal Server Error',
        501 : 'Not Implemented',
        502 : 'Bad Gateway',
        503 : 'Service Unavailable',
        504 : 'Gateway Timeout',
        505 : 'HTTP Version Not Supported',        
    }
    
    def __init__(self, code, headers = None, data = "", message = None, version = "1.1"):
        self.version = version
        self.code = code
        self.message = message
        if self.message is None:
            self.message = self.DEFAULT_MESSAGES.get(code, "No Info")
        self.headers = headers
        if self.headers is None:
            self.headers = HttpHeaders()
        self.data = data
    
    def to_text(self):
        if "content-length" not in self.headers:
            self.headers["Content-Length"] = len(self.data)
        return ("%s %s HTTP/%s\r\n" % (self.code, self.message, self.version) + 
            self.headers.to_text() + 
            self.data)

class HttpServer(object):
    def __init__(self, processor):
        self.processor = processor
    
    @reactive
    def handle_connection(self, conn):
        close = False
        try:
            while not close:
                try:
                    raw_headers = yield self.conn.read_until(("\r\n\r\n", "\n\n"))
                    header_lines = raw_headers.splitlines()
                    cmd_line = header_lines.pop(0)
                    cmd, url, proto = cmd_line.split()
                    headers = HttpHeaders.from_lines(header_lines)
                except Exception:
                    raise HttpError(400, "Bad Request")
                if "keep-alive" in headers and "content-length" in headers:
                    conn = BoundTransport(self.conn, int(headers["content-length"]), None, close_underlying = False)
                    close = False
                else:
                    conn = self.conn
                    close = True
                req = HttpRequest(cmd, url, proto, headers, conn)
                handler = getattr(self.processor, "handle_%s" % (cmd.lower(),), self._invalid_method)
                try:
                    resp = yield handler(req)
                except HttpError as ex:
                    pass
                else:
                    yield conn.write(resp.to_text())
        finally:
            self.conn.close()
    
    @classmethod
    def _invalid_method(cls, req):
        raise HttpError(405, "Method Not Allowed")



class ClientSideHttpConnection(object):
    pass


if __name__ == "__main__":
    data = """Host: net.tutsplus.com
User-Agent: Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.5) Gecko/20091102 Firefox/3.5.5 (.NET CLR 3.5.30729)
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-us,en;q=0.5
Accept-Encoding: gzip,deflate
Accept-Charset: ISO-8859-1,utf-8;q=0.7,*;q=0.7
Keep-Alive: 300
Connection: keep-alive
Cookie: PHPSESSID=r2t5uvjq435r4q7ib3vtdjq120
Pragma: no-cache
Cache-Control: no-cache

"""
    h = HttpHeaders.from_text(data)
    print data.splitlines() == h.to_text().splitlines()




