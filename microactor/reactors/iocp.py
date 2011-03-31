import itertools
import time
import socket
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
    def post(self, key = None, size = 0, overlapped = None):
        """will cause wait() to return with the given information"""
        if key is None:
            key = self._post_key
        win32file.PostQueuedCompletionStatus(self._port, size, key, overlapped)
    def wait(self, timeout):
        return win32file.GetQueuedCompletionStatus(self._port, int(timeout * 1000))

from microactor.transports import BaseTransport
from microactor.utils import Deferred

class IocpStreamTransport(BaseTransport):
    MAX_WRITE_SIZE = 32000
    MAX_READ_SIZE = 32000
    
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
            print "!! written"
            dfr.set(None)

        dfr = Deferred()
        overlapped = win32file.OVERLAPPED()
        win32file.WriteFile(self.fileno(), data, overlapped)
        overlapped.object = finished
        self._keepalive[overlapped] = finished
        return dfr
    
    def read(self, count):
        count = min(count, self.MAX_READ_SIZE)
        
        def finished(rc, size, key, overlapped):
            self._keepalive.pop(overlapped)
            print "!! read"
            data = str(buf[:size])
            dfr.set(data)
        
        dfr = Deferred()
        overlapped = win32file.OVERLAPPED()
        buf = win32file.AllocateReadBuffer(count)
        win32file.ReadFile(self.fileno(), buf, overlapped)
        overlapped.object = finished
        self._keepalive[overlapped] = finished
        return dfr

    def connect(self, host, port):
        def finished(rc, size, key, overlapped):
            self._keepalive.pop(overlapped)
            print "!! connected"
            dfr.set()
        
        self.fileobj.bind(('0.0.0.0', 0)) # ConnectEx requires sock to be bound
        dfr = Deferred()
        overlapped = win32file.OVERLAPPED()
        overlapped.object = finished
        self._keepalive[overlapped] = finished
        addr = socket.gethostbyname(host)
        win32file.ConnectEx(self.fileobj.fileno(), (addr, port), overlapped)
        return dfr

    def accept(self):
        def finished(rc, size, key, overlapped):
            self._keepalive.pop(overlapped)
            print "!! accepted"
            dfr.set(sock)
        
        dfr = Deferred()
        overlapped = win32file.OVERLAPPED()
        overlapped.object = finished
        self._keepalive[overlapped] = finished
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.reactor._iocp.register(sock)
        buffer = win32file.AllocateReadBuffer(win32file.CalculateSocketEndPointSize(sock.fileno()))
        win32file.AcceptEx(self.fileobj.fileno(), sock.fileno(), buffer, overlapped)
        
        return dfr

class IocpReactor(BaseReactor):
    def __init__(self):
        BaseReactor.__init__(self)
        self._iocp = IOCP()
    
    @classmethod
    def supported(cls):
        return hasattr(win32file, "CreateIoCompletionPort")
    
    def _handle_transports(self, timeout):
        tmax = time.time() + timeout
        while True:
            rc, size, key, overlapped = self._iocp.wait(timeout)
            if rc == win32con.WAIT_TIMEOUT:
                break
            overlapped.object(rc, size, key, overlapped)
            if time.time() > tmax:
                break
            timeout = 0
    














