import microactor


@microactor.reactive
def main(reactor):
    conn = yield reactor.tcp.connect("www.google.com", 80)
    conn.
    1/0


if __name__ == "__main__":
    cls = microactor.get_reactor_factory()
    reactor = cls()
    reactor.run(main)


