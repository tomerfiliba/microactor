import microactor
from microactor.reactors.iocp import IocpStreamTransport


if __name__ == "__main__":
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    @microactor.reactive
    def main(reactor):
        yield t.connect("www.google.com", 80)
        yield t.write("GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n")
        data = yield t.read(1000)
        print data
        reactor.stop()
    
    reactor = microactor.get_reactor("iocp")
    t = IocpStreamTransport(reactor, s)
    reactor._iocp.register(t)
    reactor.run(main)








