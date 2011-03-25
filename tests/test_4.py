import time
import microactor


@microactor.reactive
def main(reactor):
    print time.ctime(), "start"
    reactor.call_after(10, lambda job: reactor.stop())
    
    def foo(job):
        print time.ctime(), "foo"
    
    reactor.call_after(2, foo)
    
    yield reactor.threading.call(time.sleep, 5)
    print time.ctime(), "done sleeping"


if __name__ == "__main__":
    cls = microactor.get_reactor_factory()
    reactor = cls()
    reactor.run(main)


