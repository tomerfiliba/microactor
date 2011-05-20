from microactor import reactive, rreturn
from microactor.protocols.remoting import BaseService
from microactor.utils.application import WorkerApplication


class MyWorker(WorkerApplication):
    
    class Service(BaseService):
        @reactive
        def exposed_add(self, x, y):
            yield self.reactor.jobs.sleep(2)
            rreturn (x + y)
        @reactive
        def exposed_div(self, x, y):
            yield self.reactor.jobs.sleep(2)
            rreturn (x / y)
        @reactive
        def exposed_bomb(self):
            yield self.reactor.jobs.sleep(2)
            raise SystemExit()


if __name__ == "__main__":
    MyWorker.start()

