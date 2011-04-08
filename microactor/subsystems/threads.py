import itertools
import threading
from .base import Subsystem
from microactor.utils import Deferred
from Queue import Queue as ConsumerProducerQueue


class ThreadingSubsystem(Subsystem):
    NAME = "threading"
    DEFAULT_MAX_WORKERS = 10
    ID_GENERATOR = itertools.count()
    
    def _init(self):
        self._max_workers = self.DEFAULT_MAX_WORKERS
        self._workers = {}
        self._tasks = ConsumerProducerQueue()
    
    def _worker_thread(self, id):
        try:
            while True:
                func, args, kwargs, dfr = self._tasks.get()
                try:
                    res = func(*args, **kwargs)
                except Exception as ex:
                    self.reactor.call(dfr.throw, ex)
                else:
                    self.reactor.call(dfr.set, res)
        finally:
            self._workers.pop(id, None)
    
    def set_max_workers(self, num):
        self._max_workers = num
    
    def get_num_of_workers(self):
        return len(self._workers)
    
    def _spawn_workers(self):
        if len(self._tasks) <= len(self._workers):
            return
        if len(self._workers) >= self._max_workers:
            return
        needed = min(len(self._tasks) - len(self._workers), self._max_workers)
        for _ in range(needed):
            tid = self.ID_GENERATOR.next()
            thd = threading.Thread(name = "worker-%d" % (tid,), target = self._worker_thread, args = (tid,))
            thd.setDaemon()
            self._workers[tid] = thd
            thd.start()
    
    def call(self, func, *args, **kwargs):
        dfr = Deferred()
        self.tasks.put((func, args, kwargs, dfr))
        self._spawn_workers()
        return dfr







