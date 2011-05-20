import microactor
from microactor.utils import reactive
from microactor.protocols.remoting import RemotingHandler
from microactor.utils.transports import DuplexStreamTransport


def cli_switch(names, types = (), mandatory = False, requires = (), excludes = ()):
    def deco(func):
        def wrapper(*args, **kwargs):
            pass
        return wrapper
    return deco


class Application(object):
    def __init__(self, reactor):
        self.reactor = reactor

    @classmethod
    def start(cls):
        reactor = microactor.get_reactor()
        inst = cls(reactor)
        reactor.call(inst.main)
        reactor.start()
    
    @reactive
    def main(self):
        raise NotImplementedError()


class WorkerApplication(Application):
    @reactive
    def main(self):
        trns = DuplexStreamTransport(self.reactor.io.stdin, self.reactor.io.stdout)
        server = RemotingHandler(self.Service, trns)
        try:
            yield server.start()
        finally:
            self.reactor.stop()











