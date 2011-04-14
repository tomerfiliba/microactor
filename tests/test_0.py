import microactor


@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(2, reactor.stop)
    conn = yield reactor.net.connect_tcp("www.google.com", 80)
    conn.write("GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n")
    data = yield conn.read(1000)
    print data


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)


