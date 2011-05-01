import select
from .base import PosixPollingReactor


class KqueuePoller(object):
    POLLIN = 1
    POLLOUT = 2

    def __init__(self):
        self._kqueue = select.kqueue()
    
    def register(self, fd, flags):
        events = []
        if flags & self.POLLIN:
            events.append(select.kevent(fd, select.KQ_FILTER_READ, select.KQ_EV_ADD | select.KQ_EV_ENABLE))
        if flags & self.POLLOUT:
            events.append(select.kevent(fd, select.KQ_FILTER_WRITE, select.KQ_EV_ADD | select.KQ_EV_ENABLE))
        self._kqueue.control(events, 0)
    
    def modify(self, fd, flags):
        self.unregister(fd)
        self.register(fd, flags)
    
    def unregister(self, fd):
        events = [select.kevent(fd, select.KQ_FILTER_READ, select.KQ_EV_DELETE),
            select.kevent(fd, select.KQ_FILTER_WRITE, select.KQ_EV_DELETE)]
        self._kqueue.control(events, 0)
    
    def poll(self, timeout, maxevents = 100):
        return self._kqueue.control(None, maxevents, timeout)


class KqueueReactor(PosixPollingReactor):
    REGISTER_READ_MASK = KqueuePoller.POLLIN
    REGISTER_WRITE_MASK = KqueuePoller.POLLOUT
    
    def __init__(self):
        PosixPollingReactor.__init__(self)
        self._poller = KqueuePoller()
        self._install_builtin_subsystems()
    
    @classmethod
    def supported(cls):
        return hasattr(select, "kqueue")
    
    def _handle_transports(self, timeout):
        for e in self._get_events(timeout):
            trns, _ = self._registered_with_epoll[e.ident]
            if e.filter == select.KQ_FILTER_READ:
                self.call(trns.on_read)
            if e.filter == select.KQ_FILTER_WRITE:
                self.call(trns.on_write)


