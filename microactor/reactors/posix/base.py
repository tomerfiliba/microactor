import weakref
import signal
import errno
from ..base import BaseReactor, ReactorError
from .transports import WakeupTransport
from .subsystems import POSIX_SUBSYSTEMS


SIGCHLD = getattr(signal, "SIGCHLD", NotImplemented)

class PosixBaseReactor(BaseReactor):
    SUBSYSTEMS = BaseReactor.SUBSYSTEMS + POSIX_SUBSYSTEMS
    
    def __init__(self):
        BaseReactor.__init__(self)
        self._signal_handlers = {}
        self._waker = WakeupTransport(weakref.proxy(self))
    
    def _wakeup(self):
        self._waker.set()
    
    def start(self):
        self.register_read(self._waker)
        BaseReactor.start(self)
    
    #===========================================================================
    # Transports
    #===========================================================================
    def register_read(self, transport):
        raise NotImplementedError()
    def register_write(self, transport):
        raise NotImplementedError()
    def unregister_read(self, transport):
        raise NotImplementedError()
    def unregister_write(self, transport):
        raise NotImplementedError()

    #===========================================================================
    # POSIX Signals
    #===========================================================================
    def _generic_signal_handler(self, signum, frame):
        for handler in self._signal_handlers.get(signum, ()):
            if signum == SIGCHLD:
                # must be called from within the context of the signal handler
                handler(signum)
                # need to re-register the signal handler (System V)
                signal.signal(SIGCHLD, self._generic_signal_handler)
            else:
                # defer
                self.call(handler, signum)
        self._wakeup()

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


class PosixPollingReactor(PosixBaseReactor):
    REGISTER_READ_MASK = NotImplemented
    REGISTER_WRITE_MASK = NotImplemented

    def __init__(self):
        PosixBaseReactor.__init__(self)
        self._transports = {}
        self._prev_transports = {}
        self._poller = NotImplemented
    
    def _register_transport(self, transport, flags):
        fd = transport.fileno()
        if fd in self._transports:
            trns, mask = self._transports[fd]
            if trns is not transport:
                raise ReactorError("multiple transports registered for the same fd")
        else:
            mask = 0
        self._transports[fd] = (transport, mask | flags)
    
    def _unregister_transport(self, transport, flags):
        try:
            fd = transport.fileno()
        except Exception:
            # assume fd has been closed
            self._prune(transport)
            return
        if fd not in self._transports:
            return
        _, mask = self._transports[fd]
        new_mask = mask & ~flags
        if not new_mask:
            del self._transports[fd]
        else:
            self._transports[fd] = (transport, new_mask)

    def register_read(self, transport):
        self._register_transport(transport, self.REGISTER_READ_MASK)
    def register_write(self, transport):
        self._register_transport(transport, self.REGISTER_WRITE_MASK)
    def unregister_read(self, transport):
        self._unregister_transport(transport, self.REGISTER_READ_MASK)
    def unregister_write(self, transport):
        self._unregister_transport(transport, self.REGISTER_WRITE_MASK)

    def _prune(self, transport):
        for fd, (trns, _) in self._transports.items():
            if trns is transport:
                del self._transports[fd]
                break
    
    def _update_poller(self):
        for fd, (_, flags) in self._transports.items():
            if fd not in self._prev_transports:
                self._poller.register(fd, flags)
            else:
                _, prev_flags = self._prev_transports[fd]
                if flags != prev_flags:
                    self._poller.modify(fd, flags)
        for fd in self._prev_transports:
            if fd not in self._transports:
                self._poller.unregister(fd)
        self._prev_transports = self._transports.copy()
    
    def _get_events(self, timeout):
        self._update_poller()
        try:
            events = self._poller.poll(timeout)
        except EnvironmentError as ex:
            if getattr(ex, "errno", ex.args[0]) == errno.EINTR:
                events = ()
            else:
                raise
        return events


