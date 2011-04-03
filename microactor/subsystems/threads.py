import threading
from microactor.subsystems.base import Subsystem
from microactor.utils import Deferred
from microactor.lib.colls import ThreadSafeQueue


class ThreadPool(object):
    def __init__(self, reactor, num_of_threads):
        self.reactor = reactor
        self.queues = []
        self.active = True
        self.running_threads = ThreadSafeQueue()
        for i in range(num_of_threads):
            queue = ThreadSafeQueue()
            thd = threading.Thread(name = "pool-%r" % (i,), target = self._thread_pool_main)
            self.running_threads.put(thd)
            self.worker_queues.append(queue)
            thd.start()
    
    def close(self):
        self.active = False
        for queue in self.queues:
            queue.put((None, None, None, None))
        return self.reactor.threading.call(self.running_threads.join)
    
    def _thread_pool_main(self, queue):
        try:
            while self.active:
                func, args, kwargs, dfr = queue.get()
                if not self.active:
                    dfr.cancel()
                    break
                try:
                    res = func(*args, **kwargs)
                except Exception as ex:
                    dfr.throw(ex)
                else:
                    dfr.set(res)
        finally:
            self.running_threads.task_done()
    
    def _get_next_queue(self):
        return min(self.queues, key = len)
    
    def call(self, func, *args, **kwargs):
        dfr = Deferred()
        queue = self._get_next_queue()
        queue.push((func, args, kwargs, dfr))
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
                dfr.throw(ex)
            else:
                dfr.set(res)
            finally:
                self.threads.discard(thd)
        thd = threading.Thread(target = wrapper)
        self.threads.add(thd)
        thd.start()
        return dfr
    
    def thread_pool(self, size):
        return ThreadPool(self.reactor, size)








