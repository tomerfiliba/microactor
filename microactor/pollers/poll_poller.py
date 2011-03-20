import select
from .base import BasePoller


class BasePollPoller(BasePoller):
    def __init__(self, poll_obj, IN_MASK, OUT_MASK):
        self.poll_obj = poll_obj
        self.IN_MASK = IN_MASK
        self.OUT_MASK = OUT_MASK
        self.fdinfo = {}
        self.old_fdinfo = {}
        self.changeset = set()
    
    def _change(self, fileobj, flags):
        fd = fileobj.fileno()
        if fd in self.fdinfo:
            _, mask = self.fdinfo[fd]
        else:
            mask = 0
        if flags > 0:
            mask |= flags
        else:
            mask &= ~(-flags)
        self.fdinfo[fd] = (fileobj, mask)
        self.changeset.add(fd)

    def register_read(self, fileobj):
        self._change(fileobj, self.IN_MASK)
    def register_write(self, fileobj):
        self._change(fileobj, self.OUT_MASK)
    def unregister_read(self, fileobj):
        self._change(fileobj, -self.IN_MASK)
    def unregister_write(self, fileobj):
        self._change(fileobj, -self.OUT_MASK)
    
    def _update(self):
        if not self.changeset:
            return
        for fd in self.changeset:
            _, mask = self.fdinfo[fd]
            if fd in self.old_fdinfo:
                _, oldmask = self.old_fdinfo[fd]
                if mask == 0:
                    self.poll_obj.unregister(fd)
                    del self.fdinfo[fd]
                elif mask != oldmask:
                    self.poll_obj.modify(fd, mask)
            else:
                if mask == 0:
                    del self.fdinfo[fd]
                else:
                    self.poll_obj.register(fd, mask)
        self.changeset.clear()
        self.old_fdinfo.clear()
        self.old_fdinfo.update(self.fdinfo)
        
    def poll(self, timeout):
        self._update()
        events = self.poll_obj.poll(timeout)
        rlist = []
        wlist = []
        for fd, mask in events:
            fobj, _ = self.fdinfo[fd]
            if mask & self.IN_MASK:
                rlist.append(fobj)
            if mask & self.OUT_MASK:
                wlist.append(fobj)
        return rlist, wlist


class PollPoller(BasePollPoller):
    def __init__(self):
        BasePollPoller.__init__(self, select.poll(), select.POLLIN, select.POLLOUT)
    @classmethod
    def supported(cls):
        return hasattr(select, "poll")


class EpollPoller(BasePollPoller):
    def __init__(self):
        BasePollPoller.__init__(self, select.epoll(), select.EPOLLIN, select.EPOLLOUT)
    def close(self):
        self.poll_obj.close()
    @classmethod
    def supported(cls):
        return hasattr(select, "epoll")




