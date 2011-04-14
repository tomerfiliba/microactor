import time
import socket
import microactor


@microactor.reactive
def main(reactor):
    for _ in range(2):
        t0 = time.time()
        print "connecting"
        conn = yield reactor.net.connect_tcp("www.google.com", 80)
        print "connected", conn
        yield conn.write("GET / HTTP/1.1\r\nHost:www.google.com\r\n\r\n")
        data = yield conn.read(1000)
        yield conn.close()
        t1 = time.time()
        print "with reactor: ", len(data), t1 - t0
    reactor.stop()

def no_reactor():
    t0 = time.time()
    s = socket.socket()
    s.connect(("www.google.com", 443))
    s.send("GET / HTTP/1.1\r\nHost:www.google.com\r\n\r\n")
    data = s.recv(1000)
    s.close()
    t1 = time.time()
    print "without reactor:", len(data), t1-t0


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)
    from microactor.utils import Deferred
    print Deferred.ID_GENERATOR.next()
    no_reactor()


