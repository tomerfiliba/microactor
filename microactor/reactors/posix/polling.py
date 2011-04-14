import select
from .base import PosixPollingReactor


class PollReactor(PosixPollingReactor):
    REGISTER_READ_MASK = getattr(select, "POLLIN", NotImplemented)
    REGISTER_WRITE_MASK = getattr(select, "POLLOUT", NotImplemented)

    def __init__(self):
        PosixPollingReactor.__init__(self)
        self._poller = select.poll()

    @classmethod
    def supported(cls):
        return hasattr(select, "poll")

    def _handle_transports(self, timeout):
        READ_MASK = select.POLLIN | select.POLLPRI | select.POLLHUP
        
        for fd, flags in self._get_events(timeout):
            trns, _ = self._registered_with_epoll[fd]
            if flags & READ_MASK:
                self.call(trns.on_read, -1)
            if flags & select.POLLOUT:
                self.call(trns.on_write, -1)
            if flags & select.POLLERR or flags & select.POLLHUP:
                self.call(trns.on_error, None)
