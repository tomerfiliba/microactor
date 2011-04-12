import microactor


@microactor.reactive
def main(reactor):
    listener = yield reactor.net.listen_tcp(18812)
    print "listener:", listener
    reactor.call(client_main, reactor)
    while True:
        conn = yield listener.accept()
        print "accepted", conn
        reactor.call(serve_client, reactor, conn)

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
def serve_client(reactor, conn):
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
    print reactor
    reactor.jobs.schedule(5, reactor.stop)
    reactor.run(main)


