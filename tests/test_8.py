import microactor


@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(30, reactor.stop)
    print "write something: ",
    data = yield reactor.io.stdin.read(100)
    print "got", repr(data)
    

if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

