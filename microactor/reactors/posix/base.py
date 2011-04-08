import weakref
import signal
from .transports import EventTransport
from ..base import BaseReactor


class BasePosixReactor(BaseReactor):
    def __init__(self):
        BaseReactor.__init__(self)
        self._signal_handlers = {}
        self._wakeup = EventTransport(weakref.proxy(self))
    
    def wakeup(self):
        self._wakeup.set()
    
    #===========================================================================
    # Transports
    #===========================================================================
    def register_read(self, transport):
        raise NotImplementedError()
    def register_write(self, transport):
        raise NotImplementedError()

    #===========================================================================
    # POSIX Signals
    #===========================================================================
    def _generic_signal_handler(self, signum, frame):
        for handler in self._signal_handlers.get(signum, ()):
            if signum == signal.SIGCHLD:
                # must be called from within the context of the signal handler
                handler(signum)
                # need to reregister the signal handler (System V)
                signal.signal(signal.SIGCHLD, self._generic_signal_handler)
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


class PosixPollingReactor(BasePosixReactor):
    def __init__(self):
        BasePosixReactor.__init__(self)
        self._transports = {}
        self._prev_transports = {}

    def _register_transport(self, transport, flag):
        fd = transport.fileno()
        if fd in self._transports:
            trns, mask = self._transports[fd]
            assert trns is transport
        else:
            mask = 0
        self._transports[fd] = (transport, mask | flag)

    def _update_poller(self):
        self.register_read(self._wakeup)
        for fd, (_, flags) in self._transports.items():
            if fd not in self._prev_transports:
                self._epoll.register(fd, flags)
            else:
                _, prev_flags = self._prev_transports[fd]
                if flags != prev_flags:
                    self._epoll.modify(fd, flags)
        for fd in self._prev_transports:
            if fd not in self._transports:
                self._epoll.unregister(fd)
        self._prev_transports = self._transports
        self._transports = {}
    



