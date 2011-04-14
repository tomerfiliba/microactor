import time
import weakref
from functools import partial
from microactor.utils.colls import MinHeap
from microactor.subsystems import GENERIC_SUBSYSTEMS
from microactor.utils import Deferred


class ReactorError(Exception):
    pass
class UnsupportedSubsystemException(Exception):
    pass


class BaseReactor(object):
    MAX_POLLING_TIMEOUT = 0.5
    SUBSYSTEMS = GENERIC_SUBSYSTEMS

    def __init__(self):
        self._callbacks = []
        self._jobs = MinHeap()
        self._active = False
        self._subsystems = {}
        self._install_builtin_subsystems()
        self.started = Deferred(self)
    
    @classmethod
    def supported(cls):
        return False

    def _install_builtin_subsystems(self):
        for factory in self.SUBSYSTEMS:
            self.install_subsystem(factory)
    
    def install_subsystem(self, factory):
        if not factory.supported(self):
            raise UnsupportedSubsystemException(factory)
        subsys = factory(weakref.proxy(self))
        if hasattr(self, subsys.NAME):
            raise ValueError("subsystem %r masks an existing attribute" % (subsys.NAME,))
        setattr(self, subsys.NAME, subsys)
        self._subsystems[subsys.NAME] = subsys
        subsys._init()

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
        self.started.set()
        while self._active:
            self._work()
        self._shutdown()
        self._handle_callbacks()
        self.started = Deferred(self)
    
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
        if self._callbacks:
            timeout = 0
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
        self._callbacks.append(lambda: func(*args, **kwargs))

    def call_at(self, timestamp, func):
        self._jobs.push((timestamp, func))

    def install_module(self, mod):
        pass
    









