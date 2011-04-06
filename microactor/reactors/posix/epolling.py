import select
from .base import BasePosixReactor


class EpollReactor(BasePosixReactor):
    def __init__(self):
        BasePosixReactor.__init__(self)
        self._poller = select.epoll()
        self._registered_with_epoll = {}

    @classmethod
    def supported(cls):
        return False
        #return hasattr(select, "epoll")

    def _update_epoll(self):
        for trns in self._changed_transports:            
            try:
                fd = trns.fileno()
            except EnvironmentError, ex:
                # most likely transport closed -- prune it
                # (it will be removed from the epoll automatically)
                print "pruning", trns
                for fd, t in self._registered_with_epoll.items():
                    if t is trns:
                        del self._registered_with_epoll[fd]
                        break
                self._read_transports.discard(trns)
                self._write_transports.discard(trns)
                continue

            flags = 0
            if trns in self._read_transports:
                flags |= select.EPOLLIN
            if trns in self._write_transports:
                flags |= select.EPOLLOUT
            
            if flags == 0:
                if fd in self._registered_with_epoll:
                    self._poller.unregister(fd)
                    del self._registered_with_epoll[fd]
            elif fd in self._registered_with_epoll:
                _, flags2 = self._registered_with_epoll[fd]
                if flags != flags2:
                    try:
                        self._poller.modify(fd, flags)
                    except Exception, ex:
                        print ex
                        print fd, trns
                        del self._registered_with_epoll[fd]
                    self._registered_with_epoll[fd] = (trns, flags)
            else:
                self._poller.register(fd, flags)
                self._registered_with_epoll[fd] = (trns, flags)

    def _handle_transports(self, timeout):
        self._update_epoll()
        events = self._poller.poll(timeout)
        
        for fd, flags in events:
            trns, _ = self._registered_with_epoll[fd]
            if flags & select.EPOLLIN or flags & select.EPOLLPRI:
                self.call(trns.on_read, -1)
            if flags & select.EPOLLOUT:
                self.call(trns.on_write, -1)
            if flags & select.EPOLLERR or flags & select.EPOLLHUP:
                self.call(trns.on_error, None)








