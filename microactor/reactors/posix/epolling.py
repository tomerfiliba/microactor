import select
from .base import PosixPollingReactor


class EpollReactor(PosixPollingReactor):
    def __init__(self):
        PosixPollingReactor.__init__(self)
        self._poller = select.epoll()

    def register_read(self, transport):
        self._register_transport(transport, select.EPOLLIN)
    def register_write(self, transport):
        self._register_transport(transport, select.EPOLLOUT)

    @classmethod
    def supported(cls):
        return hasattr(select, "epoll")

    def _handle_transports(self, timeout):
        self._update_poller()
        events = self._poller.poll(timeout)
        
        for fd, flags in events:
            trns, _ = self._registered_with_epoll[fd]
            if flags & select.EPOLLIN or flags & select.EPOLLPRI:
                self.call(trns.on_read, -1)
            if flags & select.EPOLLOUT:
                self.call(trns.on_write, -1)
            if flags & select.EPOLLERR or flags & select.EPOLLHUP:
                self.call(trns.on_error, None)

