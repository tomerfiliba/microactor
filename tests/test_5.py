import microactor
from microactor.utils.mutex import Mutex


def sleep(reactor, interval):
    dfr = microactor.Deferred()
    def wakeup(job):
        dfr.set()
    reactor.call_after(interval, wakeup)
    return dfr

@microactor.reactive
def main(reactor):
    m = Mutex()
    yield m.acquire()
    print "main acquired"
    reactor.call(another, m)
    yield sleep(reactor, 5)
    yield m.release()
    print "main released"
    


@microactor.reactive
def another(m):
    print "another started"
    yield m.acquire()
    print "another acquired"
    yield m.release()
    print "another released"



if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)


