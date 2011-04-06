import time
import weakref
import signal
from functools import partial
from microactor.transports.events import Event
from microactor.lib import MinHeap


class ReactorError(Exception):
    pass


class BaseReactor(object):
    MAX_POLLING_TIMEOUT = 0.5

    def __init__(self):
        self._read_transports = set()
        self._write_transports = set()
        self._changed_transports = set()
        self._callbacks = []
        self._on_exit_callbacks = []
        self._jobs = MinHeap()
        self._signal_handlers = {}
        self._processes = []
        self._wakeup = Event(weakref.proxy(self))
        self._active = False
        self.register_read(self._wakeup)
    
    @classmethod
    def supported(cls):
        return False

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
        self._changed_transports.clear()
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

    def add_job(self, timestamp, func):
        self._jobs.push((timestamp, func))

    #===========================================================================
    # POSIX Signals
    #===========================================================================
    def _generic_signal_handler(self, signum, frame):
        for handler in self._signal_handlers.get(signum, ()):
            if signum == getattr(signal, "SIGCHLD", NotImplemented):
                # must be called from within the context of the signal handler
                handler(signum)
            else:
                # defer
                self.call(handler, signum)
        self._wakeup.set()

    def register_signal(self, signum, callback):
        """callback signature: (signum)"""
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







