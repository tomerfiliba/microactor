import time
import select
import errno
from .base import BasePosixReactor
from ..base import ReactorError


class SelectReactor(BasePosixReactor):
    def __init__(self):
        BasePosixReactor.__init__(self)
        self._read_transports = {}
        self._write_transports = {}

    def register_read(self, transport):
        print "register_read", transport
        fd = transport.fileno()
        if fd in self._read_transports and self._read_transports[fd] is not transport:
            raise ReactorError("multiple transports register for the same fd")
        self._read_transports[fd] = transport
    
    def register_write(self, transport):
        print "register_write", transport
        fd = transport.fileno()
        if fd in self._write_transports and self._write_transports[fd] is not transport:
            raise ReactorError("multiple transports register for the same fd")
        self._write_transports[fd] = transport

    def unregister_read(self, transport):
        fd = transport.fileno()
        self._read_transports.pop(fd, None)
        
    def unregister_write(self, transport):
        fd = transport.fileno()
        self._write_transports.pop(fd, None)
    
    @classmethod
    def supported(cls):
        return hasattr(select, "select")
    
    def _handle_transports(self, timeout):
        print "SelectReactor._handle_transports timeout =", timeout
        if not self._read_transports and not self._write_transports:
            time.sleep(timeout)
            return
        try:
            rlst, wlst, _ = select.select(self._read_transports, self._write_transports, [], timeout)
        except (select.error, EnvironmentError) as ex:
            if ex.args[0] == errno.EINTR:
                pass
            elif ex.args[0] == errno.EBADF:
                self._prune_bad_fds()
            else:
                raise
        else:
            for fd in rlst:
                self.call(self._read_transports[fd].on_read, -1)
            for fd in wlst:
                self.call(self._write_transports[fd].on_write, -1)

    def _prune_bad_fds(self):
        for transports in [self._read_transports, self._write_transports]:
            bad = set()
            for trns in transports:
                try:
                    fds = (trns.fileno(),)
                    select.select(fds, fds, fds, 0)
                except (select.error, EnvironmentError) as ex:
                    print "pruning", trns
                    bad.add(trns)
                    self.call(trns.on_error, ex)
            transports -= bad


