import select
from .base import PosixPollingReactor


class PollReactor(PosixPollingReactor):
    def __init__(self):
        PosixPollingReactor.__init__(self)
        self._poller = select.poll()

    def register_read(self, transport):
        self._register_transport(transport, select.POLLIN)
    def register_write(self, transport):
        self._register_transport(transport, select.POLLOUT)
    def unregister_read(self, transport):
        self._unregister_transport(transport, select.POLLIN)
    def unregister_write(self, transport):
        self._unregister_transport(transport, select.POLLOUT)

    @classmethod
    def supported(cls):
        return hasattr(select, "poll")

    def _handle_transports(self, timeout):
        self._update_poller()
        try:
            events = self._poller.poll(timeout)
        except EnvironmentError as ex:
            if ex.errno == errno.EINTR:
                return
        
        for fd, flags in events:
            trns, _ = self._registered_with_epoll[fd]
            if flags & select.POLLIN or flags & select.POLLPRI:
                self.call(trns.on_read, -1)
            if flags & select.POLLOUT:
                self.call(trns.on_write, -1)
            if flags & select.POLLERR or flags & select.POLLHUP:
                self.call(trns.on_error, None)
