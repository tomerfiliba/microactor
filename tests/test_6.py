import microactor


@microactor.reactive
def main(reactor):
    try:
        f = yield reactor.io.open("test_5.py", "r")
        data = yield f.read(200)
        print repr(data)
        data = yield f.read(200)
        print repr(data)
        data = yield f.read(200)
        print repr(data)
        yield f.close()
    finally:
        reactor.stop()


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    print reactor
    reactor.run(main)


