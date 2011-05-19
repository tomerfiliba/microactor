import microactor


@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(10, reactor.stop)
    pool = reactor.proc.create_pool(["python", "worker.py"], 10)
    res = yield pool.call("add", 4, 5)
    print "res is", res


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

