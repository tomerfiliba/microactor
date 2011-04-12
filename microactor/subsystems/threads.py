import itertools
import threading
from .base import Subsystem
from microactor.utils import Deferred
from Queue import Queue as ThreadSafeQueue


class ThreadingSubsystem(Subsystem):
    NAME = "threading"
    DEFAULT_MAX_WORKERS = 10
    ID_GENERATOR = itertools.count()
    
    def _init(self):
        self._max_workers = self.DEFAULT_MAX_WORKERS
        self._workers = {}
        self._tasks = ThreadSafeQueue()
    
    def _worker_thread(self, id):
        try:
            while True:
                task = self._tasks.get()
                if not task:
                    break
                func, args, kwargs, dfr = task
                try:
                    res = func(*args, **kwargs)
                except Exception as ex:
                    self.reactor.call(dfr.throw, ex)
                else:
                    self.reactor.call(dfr.set, res)
        finally:
            self._workers.pop(id, None)
    
    def set_max_workers(self, num):
        """sets the maximal number of worker threads"""
        if num > len(self._workers):
            # put required amount of "poison tasks"
            for _ in range(num - len(self._workers)):
                self._tasks.put(None)
        self._max_workers = num
    
    def get_num_of_workers(self):
        """returns the actual number of worker threads"""
        return len(self._workers)
    
    def _spawn_workers(self):
        if self._tasks.qsize() <= len(self._workers):
            return
        if len(self._workers) >= self._max_workers:
            return
        needed = min(self._tasks.qsize() - len(self._workers), self._max_workers)
        for _ in range(needed):
            tid = self.ID_GENERATOR.next()
            thd = threading.Thread(name = "worker-%d" % (tid,), target = self._worker_thread, args = (tid,))
            thd.setDaemon(True)
            self._workers[tid] = thd
            thd.start()
    
    def call(self, func, *args, **kwargs):
        """enqueues the given task into the thread pool, returns a deferred"""
        dfr = Deferred()
        self._tasks.put((func, args, kwargs, dfr))
        self._spawn_workers()
        return dfr
    
    def call_nonpooled(self, func, *args, **kwargs):
        """spawns a new thread to process the task (not going through the 
        thread pool)"""
        def nonpooled_task():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                self.reactor.call(dfr.throw, ex)
            else:
                self.reactor.call(dfr.set, res)
        
        dfr = Deferred()
        thd = threading.Thread(target = nonpooled_task)
        thd.setDaemon(True)
        thd.start()
        return dfr







