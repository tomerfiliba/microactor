from microactor.utils import reactive


class HttpHeaders(object):
    def __init__(self, *args, **kwargs):
        self._items = {}
        self.update(*args, **kwargs)
    
    @classmethod
    def from_text(cls, text):
        inst = cls()
        for line in text.splitlines():
            if not line.strip():
                continue
            k, v = line.split(":", 1)
            if "," in v:
                inst[k.strip()] = [item.strip() for item in v.split(",")]
            else:
                inst[k.strip()] = v.strip()
        return inst
    
    def emit(self):
        lines = []
        for k, v in self.items():
            if isinstance(v, (list, tuple)):
                v = ", ".join(v)
            lines.append("%s : %s" % (k, v))
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
        return self._items[name.lower()][1]
    def __setitem__(self, name, value):
        self._items[name.lower()] = (name, value)

    def clear(self):
        self._items.clear()
    def copy(self):
        return HttpHeaders(self._items().copy())
    def keys(self):
        return (k for k, v in self.items())
    def values(self):
        return (v for k, v in self.items())
    def items(self):
        return self._items.values()
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
    pass

class ServerSideHttpConnection(object):
    def __init__(self, conn):
        self.conn = conn
    
    @reactive
    def process(self):
        pass

class ClientSideHttpConnection(object):
    pass


if __name__ == "__main__":
    h = HttpHeaders.from_text("""Host: net.tutsplus.com
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
""")
    print h
    print h["Connection"]

