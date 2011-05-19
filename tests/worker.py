import microactor
from microactor import reactive, rreturn
from microactor.protocols.remoting import BaseService, RemotingHandler
from microactor.utils.transports import DuplexStreamTransport


class MyService(BaseService):
    @reactive
    def exposed_add(self, x, y):
        yield self.reactor.jobs.sleep(2)
        rreturn (x + y)
    @reactive
    def exposed_div(self, x, y):
        yield self.reactor.jobs.sleep(2)
        rreturn (x / y)

@reactive
def main(reactor):
    trns = DuplexStreamTransport(reactor.io.stdin, reactor.io.stdout)
    server = RemotingHandler(MyService, trns)
    try:
        yield server.start()
    finally:
        reactor.close()

if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

