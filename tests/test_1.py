import microactor
import time


@microactor.reactive
def main(reactor):
    for _ in range(3):
        t0 = time.time()
        conn = yield reactor.net.connect_tcp("www.google.com", 80)
        yield conn.write("GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n")
        data = yield conn.read(1000)
        t1 = time.time()
        print "reactor:", len(data), t1 - t0
    reactor.stop()

def no_reactor():
    import socket
    for _ in range(3):
        t0 = time.time()
        s=socket.socket()
        s.connect(("www.google.com", 80))
        s.send("GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n")
        data = s.recv(1000)
        t1 = time.time()
        print "no reactor:", len(data), t1 - t0


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)
    no_reactor()

