from .base import BaseTransport
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
