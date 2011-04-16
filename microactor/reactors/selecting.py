import time
import socket # required to initialize winsock on windows (for select)
import select
import errno
import weakref
from .base import BaseReactor, ReactorError
from .transports import WakeupTransport
from .subsystems import SUBSYSTEMS as SPECIFIC_SUBSYSTEMS


class SelectingReactor(BaseReactor):
    SUBSYSTEMS = BaseReactor.SUBSYSTEMS + SPECIFIC_SUBSYSTEMS
    
    def __init__(self):
        BaseReactor.__init__(self)
        self._read_transports = {}
        self._write_transports = {}
        self._waker = WakeupTransport(weakref.proxy(self))
        self.register_read(self._waker)
    
    def _wakeup(self):
        self._waker.set()
    
    def register_read(self, transport):
        fd = transport.fileno()
        if fd in self._read_transports and self._read_transports[fd] is not transport:
            raise ReactorError("multiple transports register for the same fd")
        self._read_transports[fd] = transport
    
    def register_write(self, transport):
        fd = transport.fileno()
        if fd in self._write_transports and self._write_transports[fd] is not transport:
            raise ReactorError("multiple transports register for the same fd")
        self._write_transports[fd] = transport

    def unregister_read(self, transport):
        self._read_transports.pop(transport._fileno, None)
    
    def unregister_write(self, transport):
        self._write_transports.pop(transport._fileno, None)
    
    def _handle_transports(self, timeout):
        if not self._read_transports and not self._write_transports:
            time.sleep(timeout)
            return
        try:
            rlst, wlst, _ = select.select(self._read_transports, self._write_transports, (), timeout)
        except (select.error, EnvironmentError) as ex:
            code = ex.args[0]
            if code == errno.EINTR:
                pass
            elif code == errno.EBADF:
                self._prune_bad_fds()
            else:
                raise
        else:
            for fd in rlst:
                self.call(self._read_transports[fd].on_read)
            for fd in wlst:
                self.call(self._write_transports[fd].on_write)

    def _prune_bad_fds(self):
        for transports in [self._read_transports, self._write_transports]:
            bad = []
            for fd, trns in transports.items():
                try:
                    fds = (trns.fileno(),)
                    select.select(fds, fds, fds, 0)
                except (select.error, EnvironmentError) as ex:
                    print "pruning", trns
                    self.call(trns.on_error, ex)
                    bad.append(fd)
            for trns in bad:
                transports.pop(fd, None)







