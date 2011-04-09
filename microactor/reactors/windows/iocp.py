import time
import itertools
from microactor.utils import safe_import 
from ..base import BaseReactor
win32file = safe_import("win32file")
win32con = safe_import("win32con")


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
    def post(self, key = None, size = 0, overlapped = None):
        """will cause wait() to return with the given information"""
        if key is None:
            key = self._post_key
        win32file.PostQueuedCompletionStatus(self._port, size, key, overlapped)
    def wait(self, timeout):
        """returns (rc, size, key, overlapped)"""
        return win32file.GetQueuedCompletionStatus(self._port, int(timeout * 1000))


class IocpReactor(BaseReactor):
    def __init__(self):
        BaseReactor.__init__(self)
        self._iocp = IOCP()
    
    @classmethod
    def supported(cls):
        return bool(win32file) and hasattr(win32file, "CreateIoCompletionPort")

    def register_transport(self, transport):
        self._iocp.register(transport.fileno())

    def wakeup(self):
        self._iocp.post()
    
    def _handle_transports(self, timeout):
        tmax = time.time() + timeout
        while True:
            rc, size, _, overlapped = self._iocp.wait(timeout)
            if rc == win32con.WAIT_TIMEOUT:
                break
            self.call(overlapped.object, size, overlapped)
            if time.time() > tmax:
                break
            timeout = 0
    
    








