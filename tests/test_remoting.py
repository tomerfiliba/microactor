import microactor
from microactor.protocols.remoting import BaseService, RemotingHandler,\
    RemotingClient


class MyService(BaseService):
    def exposed_add(self, x, y):
        return x + y
    def exposed_div(self, x, y):
        return x / y


@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(10, reactor.stop)
    server = yield reactor.net.serve(RemotingHandler.of(MyService), 18822)
    client = yield RemotingClient.connect(reactor, "localhost", 18822)
    print client
    res = yield client.call("add", 33, 22)
    print "res is", res
    res = yield client.call("div", 33.0, 22.0)
    print "res is", res
    res = yield client.api.add(33, 22)
    print "res is", res
    
    try:
        res = yield client.call("div", 33, 0)
    except ZeroDivisionError:
        print "OK: got exception"
    else:
        print "Error: did not get an exception!"


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

