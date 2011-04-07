import threading
from .base import Subsystem
from microactor.utils import Deferred
from Queue import Queue as ThreadSafeQueue


class ThreadPool(object):
    def __init__(self, reactor, num_of_threads):
        self.reactor = reactor
        self.active = True
        self.tasks = ThreadSafeQueue()
        self.all_done = ThreadSafeQueue()
        for i in range(num_of_threads):
            thd = threading.Thread(name = "pool-thread-%d" % (i,), target = self._thread_pool_main)
            self.all_done.put(None)
            thd.start()
    
    def close(self):
        self.active = False
        for i in range(num_of_threads):
            self.tasks.push((None, None, None, None))
        return self.reactor.threading.call(self.running_threads.join)
    
    def _thread_pool_main(self):
        try:
            while True:
                func, args, kwargs, dfr = self.tasks.get()
                if func is None:
                    break
                try:
                    res = func(*args, **kwargs)
                except Exception as ex:
                    self.reactor.call(dfr.throw, ex)
                else:
                    self.reactor.call(dfr.set, res)
        finally:
            self.all_done.task_done()
    
    def call(self, func, *args, **kwargs):
        if not self.active:
            raise Kaputen()
        dfr = Deferred()
        self.tasks.put((func, args, kwargs, dfr))
        return dfr


class ThreadingSubsystem(Subsystem):
    NAME = "threading"
    
    def _init(self):
        self.threads = set()
    
    def call(self, func, *args, **kwargs):
        dfr = Deferred()
        def wrapper():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                self.reactor.call(dfr.throw, ex)
            else:
                self.reactor.call(dfr.set, res)
            finally:
                self.threads.discard(thd)
        thd = threading.Thread(target = wrapper)
        self.threads.add(thd)
        thd.start()
        return dfr
    
    def thread_pool(self, size):
        return ThreadPool(self.reactor, size)








