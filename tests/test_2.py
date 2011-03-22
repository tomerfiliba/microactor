import microactor
from microactor.protocols.http import HttpServer, HttpError


class MyHttpServer(HttpServer):
    @microactor.reactive
    def do_get(self, req):
        print req
        data = "<http><body><h1>hello there</h1></body></http>"
        yield req.conn.write("HTTP/1.1 200 OK\r\n")
        yield req.conn.write("Content-Type: text/html; charset=utf-8\r\n")
        yield req.conn.write("content-length: %s\r\n" % (len(data),))
        yield req.conn.write("\r\n")
        yield req.conn.write(data)
        yield req.conn.flush()

    @microactor.reactive
    def do_post(self, req):
        print req
        raise HttpError(404, "Not Found")




if __name__ == "__main__":
    cls = microactor.get_reactor_factory()
    reactor = cls()
    reactor.call_after(50, lambda job: reactor.stop())
    server = MyHttpServer("/tmp", 8080)
    reactor.call(server.start, reactor)
    reactor.start()

