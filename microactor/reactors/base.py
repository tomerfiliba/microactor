import time
import weakref
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
        subsys = self.factory(weakref.proxy(self.reactor))
        if hasattr(self, subsys.NAME):
            raise ValueError("subsystem %r masks an existing attribute" % (subsys.NAME,))
        setattr(self, subsys.NAME, subsys)

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
        self._shutdown()
        self._handle_callbacks()
    
    def _shutdown(self):
        raise NotImplementedError()
    
    def wakeup(self):
        raise NotImplementedError()

    def stop(self):
        if not self._active:
            raise ReactorError("reactor not running")
        self._active = False
        self.wakeup()

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
    









