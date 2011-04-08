import time
import select
from .base import BasePosixReactor
from ..base import ReactorError


class SelectReactor(BasePosixReactor):
    def __init__(self):
        BasePosixReactor.__init__(self)
        self._read_transports = {}
        self._write_transports = {}

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
    
    @classmethod
    def supported(cls):
        return hasattr(select, "select")
    
    def _handle_transports(self, timeout):
        if not self._read_transports and not self._write_transports:
            time.sleep(timeout)
            return
        while True:
            try:
                rlst, wlst, _ = select.select(self._read_transports, self._write_transports, [], timeout)
            except (select.error, EnvironmentError):
                self._prune_bad_fds()
            else:
                break
        for fd in rlst:
            self.call(self._read_transports[fd].on_read, -1)
        for fd in wlst:
            self.call(self._write_transports[fd].on_write, -1)
        self._read_transports.clear()
        self._write_transports.clear()

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


