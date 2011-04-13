import select
import errno
from .base import PosixPollingReactor


class EpollReactor(PosixPollingReactor):
    def __init__(self):
        PosixPollingReactor.__init__(self)
        self._poller = select.epoll()

    def register_read(self, transport):
        self._register_transport(transport, select.EPOLLIN)
    def register_write(self, transport):
        self._register_transport(transport, select.EPOLLOUT)
    def unregister_read(self, transport):
        self._unregister_transport(transport, select.EPOLLIN)
    def unregister_write(self, transport):
        self._unregister_transport(transport, select.EPOLLOUT)

    @classmethod
    def supported(cls):
        return hasattr(select, "epoll")

    def _handle_transports(self, timeout):
        self._update_poller()
        try:
            events = self._poller.poll(timeout)
        except EnvironmentError as ex:
            if ex.errno == errno.EINTR:
                return
        
        READ_MASK = select.EPOLLIN | select.EPOLLPRI | select.EPOLLHUP
        for fd, flags in events:
            trns, _ = self._transports[fd]
            if flags & READ_MASK:
                self.call(trns.on_read, -1)
            if flags & select.EPOLLOUT:
                self.call(trns.on_write, -1)
            if flags & select.EPOLLERR:
                self.call(trns.on_error, None)

