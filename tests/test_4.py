import time
import ssl
import socket
import microactor


@microactor.reactive
def main(reactor):
    for i in range(2):
        t0 = time.time()
        conn = yield reactor.net.connect_ssl("www.google.com", 443)
        yield conn.write("GET / HTTP/1.1\r\nHost:www.google.com\r\n\r\n")
        data = yield conn.read(1000)
        yield conn.close()
        t1 = time.time()
        print "with reactor: ", len(data), t1 - t0
    reactor.stop()

def no_reactor():
    t0 = time.time()
    s = socket.socket()
    s2 = ssl.wrap_socket(s)
    s2.connect(("www.google.com", 443))
    s2.send("GET / HTTP/1.1\r\nHost:www.google.com\r\n\r\n")
    data = s2.recv(1000)
    s2.close()
    t1 = time.time()
    print "without reactor:", len(data), t1-t0

"""
with reactor:  388 0.98432302475
with reactor:  388 0.955207109451
without reactor: 388 0.465480804443
"""

if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)
    no_reactor()


