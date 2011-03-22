import microactor


@microactor.reactive
def main(reactor):
    reactor.call_after(2, lambda job: reactor.stop())
    
    listener = yield reactor.tcp.listen(18812)
    print "listener:", listener
    reactor.call(client_main, reactor)
    while True:
        conn = yield listener.accept()
        print "accepted", conn
        reactor.call(serve_client, reactor, conn)

@microactor.reactive
def client_main(reactor):
    print "client started"
    conn = yield reactor.tcp.connect("localhost", 18812)
    print "client connected", conn
    yield conn.write("hello world")
    data = yield conn.read(10)
    print "client got", repr(data)
    conn.close()

@microactor.reactive
def serve_client(reactor, conn):
    print "servering client", conn
    try:
        while True:
            data = yield conn.read(10)
            print "server got", repr(data)
            yield conn.write("foobar!")
    except EOFError:
        raise
    conn.close()


if __name__ == "__main__":
    cls = microactor.get_reactor_factory()
    reactor = cls()
    reactor.run(main)


