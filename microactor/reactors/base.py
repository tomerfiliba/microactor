import time
import weakref
import signal
from functools import partial
from microactor.transports.events import Event
from microactor.lib import MinHeap
from microactor.subsystems import SUBSYSTEMS, init_subsystems
from .jobs import SingleJob, PeriodicJob


HAS_SIGCHLD = hasattr(signal, "SIGCHLD")


class ReactorError(Exception):
    pass

class BaseReactor(object):
    MAX_POLLING_TIMEOUT = 0.5

    def __init__(self):
        self._read_transports = set()
        self._write_transports = set()
        self._changed_transports = set()
        self._callbacks = []
        self._jobs = MinHeap()
        self._signal_handlers = {}
        self._processes = []
        self._wakeup = Event(weakref.proxy(self))
        self._active = False
        self._on_exit_callbacks = []
        self.register_read(self._wakeup)
        if HAS_SIGCHLD:
            self._check_processes = False
            def sigchld_handler(sig):
                self._check_processes = True
            self.register_signal(signal.SIGCHLD, sigchld_handler)
        
        init_subsystems(weakref.proxy(self), SUBSYSTEMS)
    
    @classmethod
    def supported(cls):
        return False
    
    #===========================================================================
    # Core
    #===========================================================================
    def run(self, func):
        self.call(func, self)
        self.start()
    
    def start(self):
        if self._active:
            raise ReactorError("reactor already running")
        self._active = True
        while self._active:
            self._work()
        self._wakeup.reset()
        self._callbacks.extend(self._on_exit_callbacks)
        del self._on_exit_callbacks[:]
        self._handle_callbacks()
    
    def stop(self):
        if not self._active:
            raise ReactorError("reactor not running")
        self._active = False
        self._wakeup.set()

    def clock(self):
        return time.time()
    
    def _work(self):
        now = self.clock()
        timeout = self._handle_jobs(now)
        self._handle_transports(min(timeout, self.MAX_POLLING_TIMEOUT))
        self._changed_transports.clear()
        self._handle_processes()
        self._handle_callbacks()
    
    def _handle_transports(self, timeout):
        raise NotImplementedError()

    def _handle_processes(self):
        if HAS_SIGCHLD:
            if self._check_processes:
                self._check_processes = False
            else:
                return
        for proc in self._processes:
            rc = proc.poll()
            if rc is not None:
                self.call(proc.on_terminated, rc)
                self.call(self._processes.remove, proc)
    
    def _handle_jobs(self, now):
        while self._jobs:
            timestamp, job = self._jobs.peek()
            if timestamp > now:
                return timestamp - now
            self._jobs.pop()
            self.call(job, now)
        return self.MAX_POLLING_TIMEOUT
    
    def _handle_callbacks(self):
        for cb in self._callbacks:
            try:
                cb()
            except Exception as ex:
                print cb.func, cb.args
                raise
        del self._callbacks[:]

    #===========================================================================
    # Transports
    #===========================================================================
    def register_read(self, transport):
        self._read_transports.add(transport)
        self._changed_transports.add(transport)

    def unregister_read(self, transport):
        self._read_transports.discard(transport)
        self._changed_transports.add(transport)
    
    def register_write(self, transport):
        self._write_transports.add(transport)
        self._changed_transports.add(transport)
    
    def unregister_write(self, transport):
        self._write_transports.discard(transport)
        self._changed_transports.add(transport)

    #===========================================================================
    # Callbacks
    #===========================================================================
    def call(self, func, *args, **kwargs):
        self._callbacks.append(partial(func, *args, **kwargs))
    
    def call_on_exit(self, func, *args, **kwargs):
        self._on_exit_callbacks.append(partial(func, *args, **kwargs))
    
    def register_module(self, mod):
        self.call(mod.start, self)
        self.call_on_exit(mod.stop, self)

    #===========================================================================
    # Jobs
    #===========================================================================
    def add_job(self, job):
        self._jobs.push((job.get_timestamp(self.clock()), job))
    def call_after(self, interval, func, *args, **kwargs):
        job = SingleJob(weakref.proxy(self), partial(func, *args, **kwargs), self.clock() + interval)
        self.add_job(job)
        return job
    def call_every(self, interval, func, *args, **kwargs):
        job = PeriodicJob(weakref.proxy(self), partial(func, *args, **kwargs), self.clock(), interval)
        self.add_job(job)
        return job
    
    #===========================================================================
    # POSIX Signals
    #===========================================================================
    def _generic_signal_handler(self, signum, frame):
        for handler in self._signal_handlers.get(signum, ()):
            if HAS_SIGCHLD and signum == signal.SIGCHLD:
                # must be called from within this context
                handler(signum)
            else:
                # defer
                self.call(handler, signum)
        self._wakeup.set()
    
    def register_signal(self, signum, callback):
        if signum not in self._signal_handlers:
            self._signal_handlers[signum] = [callback]
            signal.signal(signum, self._generic_signal_handler)
        else:
            self._signal_handlers[signum].append(callback)

    def unregister_signal(self, signum, callback):
        self._signal_handlers[signum].remove(callback)
        if not self._signal_handlers[signum]:
            signal.signal(signum, signal.SIG_DFL)
            del self._signal_handlers[signum]    








