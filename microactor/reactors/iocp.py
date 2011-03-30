import itertools
try:
    import win32file
    import win32con
except ImportError:
    win32file = None
    win32con = None 
from .base import BaseReactor


class IOCP(object):
    def __init__(self):
        self._port = win32file.CreateIoCompletionPort(win32file.INVALID_HANDLE_VALUE, None, 0, 0)
        self._key = itertools.count()
        self._post_key = self._key.next()
    def __repr__(self):
        return "IOCP(%r)" % (self._port,)
    def register(self, handle):
        """registers the given handle with the IOCP. the handle cannot be 
        unregistered"""
        if hasattr(handle, "fileno"):
            handle = handle.fileno()
        key = self._key.next()
        win32file.CreateIoCompletionPort(handle, self._port, key, 0)
        return key
    def post(self):
        """will cause wait() to return"""
        win32file.PostQueuedCompletionStatus(self._port, 0, self._post_key, None)
    def wait(self, timeout):
        res = win32file.GetQueuedCompletionStatus(self._port, int(timeout * 1000))
        return res

from microactor.transports import BaseTransport
from microactor.utils import Deferred

class IocpStreamTransport(BaseTransport):
    WRITE_SIZE = 16000
    READ_SIZE = 16000
    
    def __init__(self, reactor, fileobj):
        BaseTransport.__init__(self, reactor)
        self.fileobj = fileobj
        self._keepalive = {}
    
    def close(self):
        self.fileobj.close()
    def fileno(self):
        return self.fileobj.fileno()
    
    def write(self, data):
        def finished(rc, size, key, overlapped):
            self._keepalive.pop(overlapped)
            dfr.set(None)

        dfr = Deferred()
        overlapped = win32file.OVERLAPPED()
        win32file.WriteFile(self.fileno(), data, overlapped)
        overlapped.object = finished
        self._keepalive[overlapped] = finished
        return dfr
    
    def read(self, count):
        def finished(rc, size, key, overlapped):
            self._keepalive.pop(overlapped)
            data = str(buf[:size])
            dfr.set(data)
        
        dfr = Deferred()
        overlapped = win32file.OVERLAPPED()
        buf = win32file.AllocateReadBuffer(count)
        win32file.ReadFile(self.fileno(), buf, overlapped)
        overlapped.object = finished
        self._keepalive[overlapped] = finished
        return dfr


class IocpReactor(BaseReactor):
    def __init__(self):
        BaseReactor.__init__(self)
        self._iocp = IOCP()
    
    @classmethod
    def supported(cls):
        return hasattr(win32file, "CreateIoCompletionPort")
    
    def _handle_transports(self, timeout):
        while True:
            rc, size, key, overlapped = self._iocp.wait(timeout)
            if rc == win32con.WAIT_TIMEOUT:
                break
            overlapped.object(rc, size, key, overlapped)
            timeout = 0




