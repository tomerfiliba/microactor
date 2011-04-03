import microactor
from microactor.modules.rpc import RPCModule, RPCService


class MyService(RPCService):
    @microactor.reactive
    def foo(self, a, b):
        return a + b
    
    @microactor.reactive
    def execute(self, code):
        pass



if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.install_module(RPCModule.over_stdio, MyService)
    reactor.start()




