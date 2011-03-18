import itertools
import select
try:
    import win32file
except ImportError:
    win32file = None


MODE_READ = 1
MODE_WRITE = 2
MODE_RW = MODE_READ | MODE_WRITE

class BasePoller(object):
    def close(self):
        pass
    @classmethod
    def supported(cls):
        return False
    def register(self, fileobj, mode = MODE_RW):
        raise NotImplementedError()
    def unregister(self, fileobj):
        raise NotImplementedError()
    def poll(self, timeout):
        raise NotImplementedError()

class SelectPoller(BasePoller):
    def __init__(self):
        self.rfiles = set()
        self.wfiles = set()
    @classmethod
    def supported(cls):
        return hasattr(select, "select")
    def register(self, fileobj, mode = MODE_RW):
        self.rfiles.discard(fileobj)
        self.wfiles.discard(fileobj)
        if mode & MODE_READ:
            self.rfiles.add(fileobj)
        if mode & MODE_WRITE:
            self.wfiles.add(fileobj)
    def unregister(self, fileobj):
        self.rfiles.discard(fileobj)
        self.wfiles.discard(fileobj)
    def poll(self, timeout):
        rl, wl, _ = select.select(self.rfiles, self.wfiles, (), timeout)
        rl = set(rl)
        wl = set(wl)
        out = []
        for f in rl.union(wl):
            mode = 0
            if f in rl:
                mode |= MODE_READ
            if f in wl:
                mode |= MODE_WRITE
            out.append((f, mode))
        return out

class UnixPoller(object):
    def __init__(self):
        self.poll = select.poll()

    @classmethod
    def supported(cls):
        return hasattr(select, "poll")
    
    def register(self, fileobj, mode = MODE_RW):
        mask = 0
        if mode & MODE_READ:
            mask |= select.POLLIN
        if mode & MODE_WRITE:
            mask |= select.POLLOUT
        self.poll.register(fileobj, mask)
    
    def unregister(self, fileobj):
        self.poll.unregister(fileobj)
    
    def poll(self, timeout):
        events = self.poll.poll(timeout)
        out = []
        for fd, mask in events:
            mode = 0
            if mask & select.POLLIN:
                mode |= MODE_READ
            if mask & select.POLLOUT:
                mode |= MODE_WRITE
            out.append((fd, mode))
        return out

class EPoller(object):
    def __init__(self):
        self.epoll = select.epoll()
        self.fdmap = {}
    
    def close(self):
        self.epoll.close()

    @classmethod
    def supported(cls):
        return hasattr(select, "epoll")
    
    def register(self, fileobj, mode = MODE_RW):
        fd = fileobj.fileno()
        mask = 0
        if mode & MODE_READ:
            mask |= select.EPOLLIN
        if mode & MODE_WRITE:
            mask |= select.EPOLLOUT
        if fd in self.fdmap:
            self.epoll.modify(fd, mask)
        else:
            self.epoll.register(fd, mask)
            self.fdmap[fd] = fileobj

    def unregister(self, fileobj):
        fd = fileobj.fileno()
        if fd not in self.fdmap:
            return
        self.epoll.unregister(fd)
        del self.fdmap[fd]
    
    def poll(self, timeout):
        events = self.epoll.poll(timeout)
        out = []
        for fd, mask in events:
            mode = 0
            if mask & select.EPOLLIN:
                mode |= MODE_READ
            if mask & select.EPOLLOUT:
                mode |= MODE_WRITE
            out.append((fd, mode))
        return out

class KQueuePoller(BasePoller):
    def __init__(self):
        self.kqueue = select.kqueue()
        self.fdmap = {}

    @classmethod
    def supported(cls):
        return hasattr(select, "kqueue")

    def close(self):
        self.kqueue.close()
    
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


class IOCPPoller(BasePoller):
    def __init__(self):
        self.port = win32file.CreateIoCompletionPort(win32file.INVALID_HANDLE_VALUE, None, 0, 0)
        self.keygen = itertools.count()
    @classmethod
    def supported(cls):
        return hasattr(win32file, "CreateIoCompletionPort")
    def close(self):
        win32file.CloseHandle(self.port)
    
    def register(self, handle):
        if hasattr(handle, "fileno"):
            handle = handle.fileno()
        key = self.keygen.next()
        win32file.CreateIoCompletionPort(handle, self.port, key, 0)
        return key
    
    def post(self):
        win32file.PostQueuedCompletionStatus(self.port, numberOfbytes, completionKey, overlapped)
    
    def poll(self, timeout):
        res = win32file.GetQueuedCompletionStatus(self.port, int(timeout * 1000))
        return res


for cls in [EPoller, KQueuePoller, IOCPPoller, UnixPoller, SelectPoller]:
    if cls.supported():
        DEFAULT_POLLER = cls
        break
else:
    DEFAULT_POLLER = None






