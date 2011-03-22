import microactor
from .base import Module
from microactor.transports import BufferedTransport, BoundTransport


class HttpRequest(object):
    def __init__(self, command, path, version, options, conn = None):
        self.command = command
        self.path = path
        self.version = version
        self.options = options
        self.conn = conn
    
    @classmethod
    def from_header(cls, data):
        lines = data.splitlines()
        proto = lines.pop(0)
        cmd, path, version = proto.split()
        options = dict(l.split(":", 1) for l in lines)
        return cls(cmd.lower(), path, version.split("/")[1], options)

class HttpError(Exception):
    def __init__(self, code, msg, options = (), data = ""):
        self.code = code
        self.msg = msg
        self.options = dict(options)
        self.data = data


class HttpServer(Module):
    def __init__(self, basepath, port = 8080):
        self.basepath = basepath
        self.port = port

    @microactor.reactive
    def start(self, reactor):
        listener = yield reactor.tcp.listen(self.port)
        print "listener:", listener
        while True:
            conn = yield listener.accept()
            print "accepted", conn
            reactor.call(self._handle_request, conn)

    @microactor.reactive
    def _handle_request(self, conn):
        print "handling client", conn
        bufconn = BufferedTransport(conn)
        raw_header = yield bufconn.read_until("\r\n\r\n", raise_on_eof = True)
        req = HttpRequest.from_header(raw_header)
        if "content-length" in req.options:
            length = int(req.options["content-length"])
            req.conn = BoundTransport(bufconn, length, None)
        else:
            req.conn = bufconn
        print "request: ", req.command, req.path, req.version
        
        try:
            if req.command == "get":
                yield self.do_get(req)
            elif req.command == "post":
                yield self.do_post(req)
            else:
                raise HttpError(400, "Bad Request")
        except HttpError as ex:
            yield conn.write("HTTP/1.1 %s %s" % (ex.code, ex.msg))
            for k, v in ex.options:
                yield conn.write("%s: %s\r\n" % (k, v))
            if "content-length" not in ex.options:
                conn.write("content-length: %d\r\n" % (len(ex.data),))
            yield conn.write("\r\n\r\n")
            yield conn.write(ex.payload)
        finally:
            yield conn.close()
    
    @microactor.reactive
    def handle_get(self, req):
        raise NotImplementedError()
    
    @microactor.reactive
    def handle_post(self, req):
        raise NotImplementedError()












