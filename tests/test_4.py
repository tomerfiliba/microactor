import microactor


@microactor.reactive
def main(reactor):
    print "main 1"
    conn = yield reactor.net.connect_tcp("www.google.com", 80)
    print "main 2", conn
    yield conn.write("GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n")
    print "main 3"
    data = yield conn.read(1000)
    print data
    reactor.stop()


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    print reactor
    reactor.run(main)

