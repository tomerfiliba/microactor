import microactor
from microactor.protocols.remoting import BaseService, RemotingServer,\
    RemotingClient


class MyService(BaseService):
    def exposed_add(self, x, y):
        return x + y
    def exposed_div(self, x, y):
        return x / y


@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(10, reactor.stop)
    server = yield reactor.net.serve(RemotingServer.of(MyService), 18822)
    client = yield RemotingClient.connect(reactor, "localhost", 18822)
    #res = yield client.call("add", 33, 22)
    #print "res is", res
    

if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

