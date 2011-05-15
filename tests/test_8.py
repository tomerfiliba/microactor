import microactor
from microactor.utils import BufferedTransport


@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(30, reactor.stop)
    print "write something: ",
    stdin = BufferedTransport(reactor.io.stdin)
    data = yield stdin.read_line(True)
    print "got", repr(data)
    reactor.stop()

if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

