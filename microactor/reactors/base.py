import time
from functools import partial
from microactor.utils.colls import MinHeap


class ReactorError(Exception):
    pass


class BaseReactor(object):
    MAX_POLLING_TIMEOUT = 0.5
    SUBSYSTEMS = []

    def __init__(self):
        self._callbacks = []
        self._jobs = MinHeap()
        self._active = False
    
    @classmethod
    def supported(cls):
        return False

    def install_subsystem(self, factory):
        pass

    #===========================================================================
    # Core
    #===========================================================================
    def run(self, func, *args, **kwargs):
        self.call(func, self, *args, **kwargs)
        self.start()

    def start(self):
        if self._active:
            raise ReactorError("reactor already running")
        self._active = True
        while self._active:
            self._work()
        self._handle_callbacks()
        self._wakeup.reset()
    
    def wakeup(self):
        raise NotImplementedError()

    def stop(self):
        if not self._active:
            raise ReactorError("reactor not running")
        self._callbacks.extend(self._on_exit_callbacks)
        del self._on_exit_callbacks[:]
        self._active = False
        self._wakeup.set()

    def _work(self):
        now = time.time()
        timeout = self._handle_jobs(now)
        self._handle_transports(min(timeout, self.MAX_POLLING_TIMEOUT))
        self._handle_callbacks()

    def _handle_transports(self, timeout):
        raise NotImplementedError()

    def _handle_jobs(self, now):
        while self._jobs:
            timestamp, cb = self._jobs.peek()
            if timestamp > now:
                return timestamp - now
            self._jobs.pop()
            self.call(cb)
        return self.MAX_POLLING_TIMEOUT

    def _handle_callbacks(self):
        callbacks = self._callbacks
        self._callbacks = []
        for cb in callbacks:
            cb()

    #===========================================================================
    # Callbacks
    #===========================================================================
    def call(self, func, *args, **kwargs):
        self._callbacks.append(partial(func, *args, **kwargs))

    def register_job(self, timestamp, func):
        self._jobs.push((timestamp, func))

    def install_module(self, mod):
        pass
    









