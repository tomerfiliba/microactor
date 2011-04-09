from microactor.utils import safe_import, Deferred
from io import BytesIO
win32file = safe_import("win32file")


class BaseTransport(object):
    __slots__ = ["reactor"]
    def __init__(self, reactor):
        self.reactor = reactor
    def close(self):
        raise NotImplementedError()
    def fileno(self):
        raise NotImplementedError()

    def on_error(self, info):
        pass


class StreamTransport(BaseTransport):
    WRITE_SIZE = 16000
    READ_SIZE = 16000
    __slots__ = ["fileobj", "_keepalive"]
    
    def __init__(self, reactor, fileobj):
        BaseTransport.__init__(self, reactor)
        self.fileobj = fileobj
        self._keepalive = {}
    def close(self):
        self.fileobj.close()
    def fileno(self):
        return self.fileobj.fileno()
    
    def read(self, count):
        count = min(count, self.MAX_READ_SIZE)
        
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
        
    def write(self, data):
        remaining = [data]
        
        def write_more():
            chunk = remaining[0][:self.MAX_WRITE_SIZE]
            overlapped = win32file.OVERLAPPED()
            win32file.WriteFile(self.fileno(), chunk, overlapped)
            overlapped.object = finished
            self._keepalive[overlapped] = finished
        
        def finished(size, overlapped):
            self._keepalive.pop(overlapped)
            print "!! written"
            remaining[0] = remaining[0][size:]
            if not remaining[0]:
                dfr.set(None)
            else:
                write_more()

        dfr = Deferred()
        write_more()
        return dfr
    



