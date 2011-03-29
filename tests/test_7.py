import microactor
from microactor.transports import BufferedTransport


@microactor.reactive
def http_get(reactor, url):
    if "://" in url:
        scheme, url = url.split("://", 1)
    else:
        scheme = "http"
    if "/" in url:
        hostinfo, url = url.split("/", 1)
    else:
        hostinfo = url
    if ":" in hostinfo:
        host, port = hostinfo.split(":", 1)
    else:
        host = hostinfo
        port = 80
    path = "/" + url
    c = yield reactor.tcp.connect(host, port)
    c2 = BufferedTransport(c)
    yield c2.write("GET %s HTTP/1.1\r\n" % (path,))
    yield c2.write("Host: %s\r\n" % (hostinfo,))
    yield c2.write("User-Agent: microactor-http/1.0\r\n")
    yield c2.write("\r\n")
    yield c2.flush()
    
    yield c2
    
    yield c2.close()
    


@microactor.reactive
def main(reactor):
    reactor.schedule(5, lambda job: reactor.stop())
    
    conn = yield reactor.tcp.connect("www.google.com", 80)
    yield conn.write("GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n")
    data = yield timed(0.1, conn.read(1000))
    print "data = ", repr(data)



if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

