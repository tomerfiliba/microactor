import select
from .base import BaseReactor


class EpollReactor(BaseReactor):
    def __init__(self):
        BaseReactor.__init__(self)
        self._poller = select.epoll()
        self._registered_with_epoll = {}

    @classmethod
    def supported(cls):
        return hasattr(select, "epoll")

    def _update_epoll(self):
        for trns in self._changed_transports:
            flags = 0
            if trns in self._read_transports:
                flags |= select.EPOLLIN
            if trns in self._write_transports:
                flags |= select.EPOLLOUT
            fd = trns.fileno()
            if flags == 0:
                if fd in self._registered_with_epoll:
                    self._poller.unregister(fd)
                    del self._registered_with_epoll[fd]
            elif fd in self._registered_with_epoll:
                _, flags2 = self._registered_with_epoll[fd]
                if flags != flags2:
                    self._poller.modify(fd, flags)
                    self._registered_with_epoll[fd] = (trns, flags)
            else:
                self._poller.register(fd, flags)
                self._registered_with_epoll[fd] = (trns, flags)

    def _handle_transports(self, timeout):
        self._update_epoll()
        events = self._poller.poll(timeout)
        
        for fd, flags in events:
            trns, _ = self._registered_with_epoll[fd]
            if flags & select.EPOLLIN or flags & EPOLLPRI:
                self.call(trns.on_read, -1)
            if flags & select.EPOLLOUT:
                self.call(trns.on_write, -1)
            if flags & select.EPOLLERR or flags & select.EPOLLHUP:
                self.call(trns.on_error, None)








