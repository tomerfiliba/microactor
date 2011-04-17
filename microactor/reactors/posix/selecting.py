import time
import select
import errno
from .base import PosixBaseReactor, ReactorError


class SelectReactor(PosixBaseReactor):
    def __init__(self):
        PosixBaseReactor.__init__(self)
        self._read_transports = {}
        self._write_transports = {}
    
    @classmethod
    def supported(cls):
        return hasattr(select, "select")
    
    def register_read(self, transport):
        fd = transport.fileno()
        if fd in self._read_transports and self._read_transports[fd] is not transport:
            raise ReactorError("multiple transports registered for the same fd")
        self._read_transports[fd] = transport
    
    def register_write(self, transport):
        fd = transport.fileno()
        if fd in self._write_transports and self._write_transports[fd] is not transport:
            raise ReactorError("multiple transports registered for the same fd")
        self._write_transports[fd] = transport

    def unregister_read(self, transport):
        try:
            fd = transport.fileno()
        except EnvironmentError:
            self._prune_bad_fds()
        else:
            self._read_transports.pop(fd, None)
    
    def unregister_write(self, transport):
        try:
            fd = transport.fileno()
        except EnvironmentError:
            self._prune_bad_fds()
        else:
            self._write_transports.pop(fd, None)
    
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







