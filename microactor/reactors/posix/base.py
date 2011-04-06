import weakref
import signal
from .transports import EventTransport
from ..base import BaseReactor


class BasePosixReactor(BaseReactor):
    def __init__(self):
        BaseReactor.__init__(self)
        self._read_transports = set()
        self._write_transports = set()
        self._changed_transports = set()
        self._signal_handlers = {}
        self._wakeup = EventTransport(weakref.proxy(self))
        self.register_read(self._wakeup)
    
    def wakeup(self):
        self._wakeup.set()
    
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





