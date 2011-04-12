import microactor


@microactor.reactive
def main(reactor):
    server = yield reactor.net.serve_tcp(18812, serve_client)
    print "listener:", server
    reactor.call(client_main, reactor)

@microactor.reactive
def client_main(reactor):
    print "client started"
    conn = yield reactor.net.connect_tcp("localhost", 18812)
    print "client connected", conn
    yield conn.write("hello world")
    data = yield conn.read(10)
    print "client got", repr(data)
    conn.close()

@microactor.reactive
def serve_client(conn):
    print "servering client", conn
    while True:
        data = yield conn.read(10)
        if not data:
            print "client disconnected"
            break
        print "server got", repr(data)
        yield conn.write("foobar!")
    conn.close()


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.jobs.schedule(5, reactor.stop)
    reactor.run(main)


