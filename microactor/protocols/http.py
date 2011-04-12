import microactor
from .base import Module
from microactor.transports import BufferedTransport, BoundTransport
from urlparse import urlparse


class HttpRequest(object):
    def __init__(self, command, path, version, options, conn = None):
        self.command = command
        self.path = path
        self.version = version
        self.options = options
        self.conn = conn
    
    def __repr__(self):
        return "<HttpRequest %s %r>" % (self.command, self.path)
    
    @classmethod
    def from_header(cls, data):
        lines = data.splitlines()
        proto = lines.pop(0)
        cmd, path, version = proto.split()
        options = dict(l.split(":", 1) for l in lines)
        return cls(cmd.lower(), path, version.split("/")[1], options)


class HttpResponse(object):
    def __init__(self, data, code = 200, message = "OK", options = None):
        self.code = code
        self.message = message
        self.data = data
        self.options = {}
        if options:
            for k, v in options.items():
                self[k] = v
    
    def __contains__(self, name):
        return name.lower() in self.options
    def __getitem__(self, name):
        return self.options[name.lower()]
    def __delitem__(self, name):
        del self.options[name.lower()]
    def __setitem__(self, name, value):
        self.options[name.lower()] = value
    
    @microactor.reactive
    def send(self, conn):
        if "content-length" not in self:
            try:
                self["content-length"] = len(self.data)
            except TypeError:
                pass
        if "content-type" not in self:
            self["content-type"] = ["text/html", "charset=utf-8"]            
        yield conn.write("HTTP/1.1 %s %s\r\n" % (self.code, self.message))
        for k, v in self.options.items():
            if isinstance(v, (tuple, list)):
                v = "; ".join(str(item) for item in v)
            yield conn.write("%s: %s\r\n" % (k, v))
        yield conn.write("\r\n")
        yield conn.write(self.data)
        yield conn.flush()


class HttpError(Exception):
    def __init__(self, code, msg, options = None, data = ""):
        self.resp = HttpResponse(data, code = code, message = msg, options = options)
    @microactor.reactive
    def send(self, conn):
        if not self.resp.data:
            self.resp.data = "<html><body>%s</body></html>" % (self.resp.message,)
        yield self.resp.send(conn)


class HttpServer(Module):
    def __init__(self, basepath, port = 8080):
        self.basepath = basepath
        self.port = port

    @microactor.reactive
    def start(self, reactor):
        listener = yield reactor.tcp.listen(self.port)
        self.active = True
        while self.active:
            conn = yield listener.accept()
            reactor.call(self._handle_requests, conn)
        yield listener.close()
    
    def stop(self):
        self.active = False
    
    @microactor.reactive
    def _handle_requests(self, conn):
        bufconn = BufferedTransport(conn)
        try:
            while True:
                yield self._handle_one_request(bufconn)
        except EOFError:
            pass
        finally:
            yield bufconn.close()

    @microactor.reactive
    def _handle_one_request(self, conn):
        raw_header = yield conn.read_until("\r\n\r\n", raise_on_eof = True)
        req = HttpRequest.from_header(raw_header)
        if "content-length" in req.options:
            length = int(req.options["content-length"])
            req.conn = BoundTransport(conn, length, None)
            closed_on_finish = False
        else:
            req.conn = conn
            closed_on_finish = True

        try:
            if req.command == "get":
                resp = yield self.handle_get(req)
            elif req.command == "post":
                resp = yield self.handle_post(req)
            else:
                raise HttpError(400, "Bad Request")
            yield resp.send(conn)
        except HttpError as ex:
            yield ex.send(conn)
        except Exception, ex:
            ex2 = HttpError(500, "Server Error", data = str(ex))
            ex2.send(conn)
        finally:
            if closed_on_finish: # no content-length, close the socket
                raise EOFError()
    
    @microactor.reactive
    def handle_get(self, req):
        raise NotImplementedError()
    
    @microactor.reactive
    def handle_post(self, req):
        raise NotImplementedError()



















