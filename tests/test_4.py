import microactor


@microactor.reactive
def main(reactor):
    reactor.call_after(5, lambda j: reactor.stop())
    conn = yield reactor.tcp.connect("www.google.co.il", 80)
    yield conn.write("GET / HTTP/1.1\r\n")
    yield conn.write("Host: www.google.co.il\r\n")
    print "===1"
    1/0
    print "===2"
    yield conn.write("\r\n")
    data = yield conn.read(700)
    print data



if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)


