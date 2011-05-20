import microactor
from microactor.subsystems.processes import WorkerProcessTerminated


@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(10, reactor.stop)
    pool = reactor.proc.create_pool(["python", "worker.py"], 10)
    res = yield pool.call("add", 4, 5)
    print "res is", res

    try:
        res = yield pool.call("div", 4, 0)
    except ZeroDivisionError:
        print "OK: got exception"
    else:
        print "ERRRO: did not get an exception"

    res = yield pool.call("div", 16, 2)
    print "res is", res
    
    # this would kill the worker process
    try:
        res = yield pool.call("bomb")
    except WorkerProcessTerminated:
        print "OK: worker has died"
    else:
        print "ERROR: did not get an exception"
    
    pool.close()


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

