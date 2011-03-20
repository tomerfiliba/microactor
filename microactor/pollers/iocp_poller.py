import itertools
from .base import BasePoller
try:
    import win32file
except ImportError:
    win32file = None


class IocpPoller(BasePoller):
    def __init__(self):
        self.port = win32file.CreateIoCompletionPort(win32file.INVALID_HANDLE_VALUE, None, 0, 0)
        self.keygen = itertools.count()
    @classmethod
    def supported(cls):
        #return hasattr(win32file, "CreateIoCompletionPort")
        return False
    def close(self):
        win32file.CloseHandle(self.port)
    
    def register(self, handle):
        if hasattr(handle, "fileno"):
            handle = handle.fileno()
        key = self.keygen.next()
        win32file.CreateIoCompletionPort(handle, self.port, key, 0)
        return key
    
    def unregister(self, fileobj):
        # not supported on windows
        pass
    
    def post(self):
        #win32file.PostQueuedCompletionStatus(self.port, numberOfbytes, completionKey, overlapped)
        pass
    
    def poll(self, timeout):
        res = win32file.GetQueuedCompletionStatus(self.port, int(timeout * 1000))
        return res
