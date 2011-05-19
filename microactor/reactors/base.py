import sys
import time
import weakref
from microactor.utils.colls import MinHeap
from microactor.utils import ReactorDeferred
from microactor.subsystems import GENERIC_SUBSYSTEMS


class ReactorError(Exception):
    pass

class BaseReactor(object):
    if sys.platform == "win32":
        MAX_TIMEOUT = 0.2   # to process Ctrl+C
    else:
        MAX_TIMEOUT = 1
    SUBSYSTEMS = GENERIC_SUBSYSTEMS
    
    def __init__(self):
        self._active = False
        self._jobs = MinHeap()
        self._callbacks = []
        #self._rcallbacks = []
        self._subsystems = []
        self.started = ReactorDeferred(weakref.proxy(self))

    @classmethod
    def supported(cls):
        return False
    
    #===========================================================================
    # Core
    #===========================================================================
    def install_subsystem(self, factory):
        subs = factory(weakref.proxy(self))
        if hasattr(self, subs.NAME):
            raise ValueError("attribute %r already exists" % (subs.NAME,))
        setattr(self, subs.NAME, subs)
        subs._init()
        self._subsystems.append(subs.NAME)
    
    def uninstall_subsystem(self, name):
        subs = getattr(self, name)
        subs._unload()
        #subs.reactor = None
    
    def _install_builtin_subsystems(self):
        for factory in self.SUBSYSTEMS:
            self.install_subsystem(factory)
    
    def start(self):
        if self._active:
            raise ReactorError("reactor already running")
        self._active = True
        self.started.set()
        try:
            while self._active:
                self._work()
        except KeyboardInterrupt:
            pass
        finally:
            self._active = False
    
    def stop(self):
        if not self._active:
            return
        self._active = False
        self.started.cancel()
        for name in self._subsystems:
            self.call(self.uninstall_subsystem, name)
        self._wakeup()
    
    def run(self, func):
        self.call(func, self)
        self.start()
    
    #===========================================================================
    # Internal
    #===========================================================================
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
        for cb, args, kwargs in callbacks:
            cb(*args, **kwargs)
    
    #===========================================================================
    # Callbacks
    #===========================================================================
    def call(self, func, *args, **kwargs):
        self._callbacks.append((func, args, kwargs))
    def call_at(self, ts, func, *args, **kwargs):
        self._jobs.push((ts, func, args, kwargs))
    
    













