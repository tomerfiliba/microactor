import time
import os
import signal
from functools import partial
from .pollers import get_default_poller
from .lib import MinHeap
from .jobs import SingleJob, PeriodicJob


class Reactor(object):
    def __init__(self, poller_factory = get_default_poller()):
        self._active = False
        self._poller = poller_factory()
        self._jobs = MinHeap()
        self._callbacks = []
        self._signal_handlers = {}
        self._wakeup = AutoResetEvent()
        self.register_read(self._wakeup)
    
    #===========================================================================
    # Core
    #===========================================================================
    def run(self):
        assert not self._active
        self._active = True
        while self._active:
            self._work()
    
    def close(self):
        if self._active:
            self._active = False
            self._poller.close()
    
    MAX_POLL_TIMEOUT = 1
    
    def _work(self):
        now = time.time()
        timeout = self._handle_jobs(now)
        self._handle_transports(timeout)
        self._handle_callbacks()
    
    def _handle_jobs(self, now):
        while self._jobs:
            job = self._jobs.peek_min()
            if job.timestamp > now:
                return job.timestamp - now
            else:
                job = self._jobs.pop_min()
                self.call(job.invoke, now)
        return self.MAX_POLL_TIMEOUT
    
    def _handle_transports(self, timeout):
        rlist, wlist = self._poller.poll(min(timeout, self.MAX_POLL_TIMEOUT))
        for trns in rlist:
            self.call(trns.on_read)
        for trns in wlist:
            self.call(trns.on_write)
    
    def _handle_callbacks(self):
        for cb in self._callbacks:
            cb()
        del self._callbacks[:]
    
    #===========================================================================
    # Transports
    #===========================================================================
    def register_read(self, transport):
        self._poller.register_read(transport)
    def register_write(self, transport):
        self._poller.register_write(transport)
    def unregister_read(self, transport):
        self._poller.unregister_read(transport)
    def unregister_write(self, transport):
        self._poller.unregister_write(transport)
    
    #===========================================================================
    # Callbacks and Jobs
    #===========================================================================
    def add_job(self, job):
        self.jobs.push((job.get_timestamp(), job))
        return job
    def call(self, func, *args, **kwargs):
        self._callbacks.append(partial(func, *args, **kwargs))
    def call_in(self, interval, func, *args, **kwargs):
        return self.add_job(SingleJob(interval, partial(func, *args, **kwargs)))
    def call_every(self, interval, func, *args, **kwargs):
        return self.add_job(PeriodicJob(interval, partial(func, *args, **kwargs)))
    
    #===========================================================================
    # POSIX Signals
    #===========================================================================
    def _generic_signal_handler(self, signum, frame):
        for handler in self._signal_handlers[signum]:
            if signum == getattr(signal, "SIGCHLD", -1):
                # must be called from within this context
                handler(signum)
            else:
                # defer
                self.call(handler, signum)
        self._wakeup.set()
    
    def register_signal(self, signum, callback):
        if signum not in self._signal_handlers[signum]:
            self._signal_handlers[signum] = [callback]
            signal.signal(signum, self._generic_signal_handler)
        else:
            self._signal_handlers[signum].append(callback)

    def unregister_signal(self, signum, callback):
        self._signal_handlers[signum].remove(callback)
        if not self._signal_handlers[signum]:
            signal.signal(signum, signal.SIG_DFL)
            del self._signal_handlers[signum]











