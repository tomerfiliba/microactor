import select
import socket   # needed for windows, in order for select to work
import time
from .base import BaseReactor


class SelectReactor(BaseReactor):
    @classmethod
    def supported(cls):
        return hasattr(select, "select")
    
    def _handle_transports(self, timeout):
        if not self._read_transports and not self._write_transports:
            time.sleep(timeout)
            return
        try:
            rlst, wlst, _ = select.select(self._read_transports, self._write_transports, [], timeout)
        except (select.error, EnvironmentError):
            self._prune_bad_fds()
            return
        for trns in rlst:
            self.call(trns.on_read, -1)
        for trns in wlst:
            self.call(trns.on_write, -1)

    def _prune_bad_fds(self):
        for transports in [self._read_transports, self._write_transports]:
            bad = set()
            for trns in transports:
                fds = (trns.fileno(),)
                try:
                    select.select(fds, fds, fds, 0)
                except (select.error, EnvironmentError) as ex:
                    bad.add(trns)
                    self.call(trns.on_error, ex)
            transports -= bad









