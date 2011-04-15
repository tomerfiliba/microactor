import time
from microactor.utils.colls import MinHeap


class ReactorError(Exception):
    pass

class BaseReactor(object):
    MAX_TIMEOUT = 0.5
    
    def __init__(self):
        self._active = False
        self._jobs = MinHeap()
        self._callbacks = []
    
    def start(self):
        if self._active:
            raise ReactorError("reactor already running")
        self._active = True
        try:
            while self._active:
                self._work()
        finally:
            self._active = False
    
    def stop(self):
        if not self._active:
            return
        self._active = False
        self._wakeup()
    
    def _wakeup(self):
        raise NotImplementedError()
    
    def _work(self):
        now = time.time()
        timeout = self._process_jobs(now)
        if self._callbacks:
            timeout = 0
        self._handle_transports(min(timeout, self.MAX_TIMEOUT))
        self._process_callbacks()
    
    def _process_jobs(self, now):
        while self._jobs:
            ts, func, args, kwargs  = self._jobs.peek()
            if now < ts:
                return ts - now
            self._jobs.pop()
            self._callbacks.append((func, args, kwargs))
        return self.MAX_TIMEOUT
    
    def _process_callbacks(self):
        callbacks = self._callbacks
        self._callbacks = []
        for cb, arg, kwargs in callbacks:
            cb(*arg, **kwargs)
    
    def call(self, func, *args, **kwargs):
        self._callbacks.append((func, args, kwargs))
    def call_at(self, ts, func, *args, **kwargs):
        self._jobs.push((ts, func, args, kwargs))
















