import microactor
from microactor.modules.http import HttpServer, HttpResponse, HttpError


class MyHttpServer(HttpServer):
    @microactor.reactive
    def handle_get(self, req):
        print "!! handle_get", req
        if req.path != "/" :
            raise HttpError(404, "Not Found")
        resp = HttpResponse("<http><body><h1>hello there</h1></body></http>")
        microactor.rreturn(resp)


if __name__ == "__main__":
    import signal
    reactor = microactor.get_reactor()
    @microactor.reactive
    def shutdown(*args):
        yield server.stop()
        reactor.stop()
    reactor.register_signal(signal.SIGINT, shutdown)
    reactor.call_after(50, shutdown)
    server = MyHttpServer("/tmp", 8080)
    reactor.call(server.start, reactor)
    reactor.start()

