import microactor


class HttpRequest(object):
    def __init__(self, command, path, version, options, payload = None, conn = None):
        self.command = command
        self.path = path
        self.version = version
        self.options = options
        self.payload = payload
        self.conn = conn
    
    @classmethod
    def from_header(cls, data):
        lines = data.splitlines()
        proto = lines.pop(0)
        cmd, path, version = proto.split()
        options = dict(l.split(":", 1) for l in lines)
        return cls(cmd.lower(), path, version.split("/")[1], options)


class Http(object):
    def __init__(self, basepath, port = 8080):
        self.basepath = basepath
        self.port = port
    
    @microactor.reactive
    def start(self, reactor):
        listener = yield reactor.tcp.listen(self.port)
        while True:
            conn = yield listener.accept()
            reactor.call(self._handle_request, reactor, conn)

    @microactor.reactive
    def _handle_request(self, reactive, conn):
        bufconn = BufferedReader(conn)
        raw_header = yield bufconn.read_until("\r\n\r\n")
        req = HttpRequest.from_header(raw_header)
        if req.version == "1.1":
            length = int(req.options["content-length"])
            data = bufconn.readn(length)
        else:
            data = bufconn.read_all()
        req.payload = data
        req.conn = conn
        try:
            if req.command == "get":
                yield self.do_get(req)
            elif req.command == "post":
                yield self.do_post(req)
            else:
                yield conn.write("HTTP/1.1 500 Invalid command")
        finally:
            conn.close()
    
    @microactor.yield
    def handle_get(self, req):
        raise NotImplementedError()
    
    @microactor.yield
    def handle_post(self, req):
        raise NotImplementedError()


class MyHttpServer(Http):
    @microactor.yield
    def do_get(self, req):
        yield req.conn.write("HTTP/1.1 404 Page not found")




if __name__ == "__main__":
    server = MyHttpServer()
    reactor.call(server.start, reactor)











