import select
from .base import PosixPollingReactor


class KqueuePoller(object):
    def __init__(self):
        self._kqueue = select.kqueue()
    
    def register(self, fd, flags):
        events = []
        if flags & select.POLLIN:
            events.append(select.kevent(fd, select.KQ_FILTER_READ, select.KQ_EV_ADD | select.KQ_EV_ENABLE))
        if flags & select.POLLOUT:
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
    def __init__(self):
        PosixPollingReactor.__init__(self)
        self._poller = KqueuePoller()
    
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
        return hasattr(select, "kqueue")
    
    def _handle_transports(self, timeout):
        self._update_poller()
        events = self._poller.poll(timeout)
        
        for e in events:
            trns, _ = self._registered_with_epoll[e.ident]
            if e.filter == select.KQ_FILTER_READ:
                self.call(trns.on_read, -1)
            if e.filter == select.KQ_FILTER_WRITE:
                self.call(trns.on_write, -1)





