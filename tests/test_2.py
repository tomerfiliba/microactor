import microactor


@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(2, reactor.stop)
    listener = yield reactor.net.listen_tcp(12345)
    reactor.call(do_client, reactor)
    while True:
        conn = yield listener.accept()
        print "server accepted", conn
        reactor.call(handle_client, conn)

@microactor.reactive
def do_client(reactor):
    conn = yield reactor.net.connect_tcp("localhost", 12345)
    yield conn.write("foobar")
    data = yield conn.read(100)
    print "client got", repr(data)
    conn.close()
    print "client quits"

@microactor.reactive
def handle_client(conn):
    data = yield conn.read(100)
    print "server got", repr(data)
    yield conn.write("hello " + data)
    conn.close()
    print "server quits"


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)
