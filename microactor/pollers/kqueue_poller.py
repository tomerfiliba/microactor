import select
from .base import BasePoller


class KqueuePoller(BasePoller):
    def __init__(self):
        self.kqueue = select.kqueue()
        self.fdmap = {}

    @classmethod
    def supported(cls):
        return hasattr(select, "kqueue")

    def close(self):
        self.kqueue.close()

"""    
    def register(self, fileobj, mode = MODE_RW):
        fd = fileobj.fileno()
        if fd in self.fdmap:
            self.unregister(fileobj)
        self.fdmap[fd] = fileobj
        kevents = []
        if mode & MODE_READ:
            kevents.append(select.kevent(fd, select.KQ_FILTER_READ, 
                select.KQ_EV_ADD | select.KQ_EV_ENABLE))
        if mode & MODE_WRITE:
            kevents.append(select.kevent(fd, select.KQ_FILTER_WRITE, 
                select.KQ_EV_ADD | select.KQ_EV_ENABLE))
        self.kqueue.control(kevents, 0)
    
    def unregister(self, fileobj):
        fd = fileobj.fileno()
        if fd not in self.fdmap:
            return
        del self.fdmap[fd]
        kev1 = select.kevent(fd, select.KQ_FILTER_READ, select.KQ_EV_DELETE)
        kev2 = select.kevent(fd, select.KQ_FILTER_WRITE, select.KQ_EV_DELETE)
        self.kqueue.control([kev1, kev2], 0)
    
    def poll(self, timeout):
        events = self.kqueue.control(None, 50, timeout)
        out = {}
        for e in events:
            if e.ident not in out:
                out[e.ident] = 0
            if e.filter == select.KQ_FILTER_READ:
                out[e.ident] = MODE_READ
            elif e.filter == select.KQ_FILTER_WRITE:
                out[e.ident] = MODE_WRITE
        return [(self.fdmap[fd], mode) for fd, mode in out.items()]
"""







