import select
from .base import PosixPollingReactor


class EpollReactor(PosixPollingReactor):
    REGISTER_READ_MASK = getattr(select, "EPOLLIN", NotImplemented)
    REGISTER_WRITE_MASK = getattr(select, "EPOLLOUT", NotImplemented)
    
    def __init__(self):
        PosixPollingReactor.__init__(self)
        self._poller = select.epoll()

    @classmethod
    def supported(cls):
        return hasattr(select, "epoll")

    def _handle_transports(self, timeout):
        READ_MASK = select.EPOLLIN | select.EPOLLPRI | select.EPOLLHUP
        
        for fd, flags in self._get_events(timeout):
            trns, _ = self._transports[fd]
            if flags & READ_MASK:
                self.call(trns.on_read, -1)
            if flags & select.EPOLLOUT:
                self.call(trns.on_write, -1)
            if flags & select.EPOLLERR:
                self.call(trns.on_error, None)

