import microactor


cls = microactor.get_reactor_factory()
reactor = cls()

@microactor.reactive
def main():
    listener = yield reactor.tcp.listen(18812)
    print "listener:", listener
    reactor.call(client_main)
    while True:
        client = yield listener.accept()
        print "accepted", client
        reactor.call(serve_client, client)

@microactor.reactive
def client_main():
    print "client started"
    conn = yield reactor.tcp.connect("localhost", 18812)
    print "client connected", conn
    yield conn.write("hello world")
    data = yield conn.read(10)
    print "client got", repr(data)

@microactor.reactive
def serve_client(conn):
    data = yield conn.read(10)
    print "server got", repr(data)
    yield conn.write("foobar!")
    conn.close()


if __name__ == "__main__":
    reactor.call(main)
    reactor.run()
