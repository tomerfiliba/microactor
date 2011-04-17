import threading
import itertools
from Queue import Queue 
from microactor.utils import ReactorDeferred
from .base import Subsystem


class ThreadPoolSubsystem(Subsystem):
    NAME = "threadpool"
    DEFAULT_MAX_WORKERS = 10
    ID_GENERATOR = itertools.count()
    
    def _init(self):
        self._workers = {}
        self._tasks = Queue()
        self._max_workers = self.DEFAULT_MAX_WORKERS
    
    def get_num_of_workers(self):
        return len(self._workers)
    
    def set_max_workers(self, count):
        self._max_workers = count
        if count < len(self._workers):
            for _ in range(len(self._workers) - count):
                self._tasks.put(None)
    
    def _spawn_workers(self):
        if self._tasks.qsize() <= len(self._workers):
            return
        if len(self._workers) >= self._max_workers:
            return
        needed = min(self._tasks.qsize() - len(self._workers), self._max_workers)
        for _ in range(needed):
            tid = self.ID_GENERATOR.next()
            thd = threading.Thread(name = "pooled-thread %d" % (tid,), target = self._worker_thread, args = (tid,))
            thd.setDaemon(True)
            self._workers[tid] = thd
            thd.start()

    def _worker_thread(self, id):
        try:
            while True:
                task = self._tasks.get()
                if not task:
                    break
                dfr, func, args, kwargs = task
                try:
                    res = func(*args, **kwargs)
                except Exception as ex:
                    dfr.throw(ex)
                else:
                    dfr.set(res)
                self.reactor._wakeup()
        finally:
            self._workers.pop(id, None)
    
    def call(self, func, *args, **kwargs):
        dfr = ReactorDeferred(self.reactor)
        self._tasks.put((dfr, func, args, kwargs))
        self._spawn_workers()
        return dfr


class ThreadingSubsystem(Subsystem):
    NAME = "threading"
    ID_GENERATOR = itertools.count()
    
    def _init(self):
        self._threads = set()
    
    def call(self, func, *args, **kwargs):
        def worker():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(res)
            finally:
                self._threads.discard(thd)
            self.reactor._wakeup()
        
        dfr = ReactorDeferred(self.reactor)
        tid = self.ID_GENERATOR.next()
        thd = threading.Thread(name = "thread-%d" % (tid,), target = worker)
        self._threads.add(thd)
        thd.setDaemon(True)
        thd.start()
        return dfr






