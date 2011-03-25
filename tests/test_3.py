import microactor


class Listener(object):
    def __init__(self, port):
        self.port = port
        self.listener = None
    @microactor.reactive
    def __enter__(self):
        self.listener = yield reactor.tcp.listen(self.port)
        print "__enter__", self.listener
        microactor.rreturn(self.listener)
    @microactor.reactive
    def __exit__(self, t, v, tb):
        print "__exit__"
        yield self.listener.close()

@microactor.reactive
def main(reactor):
    reactor.call_after(5, lambda job: reactor.stop())
    
    with (yield Listener(18812)) as listener:
        print "listener", listener
        reactor.call(client_main, reactor)
        while True:
            conn = yield listener.accept()
            print "accepted", conn
            reactor.call(serve_client, reactor, conn)


@microactor.reactive
def client_main(reactor):
    conn = yield reactor.tcp.connect("localhost", 18812)
    print "client", conn
    yield conn.write("hello world")
    print "client wrote"
    data = yield conn.read(10)
    print "client got", repr(data)
    conn.close()

@microactor.reactive
def serve_client(reactor, conn):
    print "serving", conn
    while True:
        data = yield conn.read(10)
        print "server got", repr(data)
        if not data:
            break
        yield conn.write("foobar!")
    conn.close()


if __name__ == "__main__":
    cls = microactor.get_reactor_factory()
    reactor = cls()
    reactor.run(main)


