from microactor.utils import safe_import, Deferred
win32file = safe_import("win32file")


class BaseTransport(object):
    __slots__ = ["reactor"]
    def __init__(self, reactor):
        self.reactor = reactor
    def _register(self):
        self.reactor.register_transport(self)
    def close(self):
        raise NotImplementedError()
    def fileno(self):
        raise NotImplementedError()

    def on_error(self, info):
        pass


class StreamTransport(BaseTransport):
    MAX_WRITE_SIZE = 32000
    MAX_READ_SIZE = 32000
    __slots__ = ["fileobj", "_keepalive"]
    
    def __init__(self, reactor, fileobj):
        BaseTransport.__init__(self, reactor)
        self.fileobj = fileobj
        self._keepalive = {}
        self._register()
    def close(self):
        self.fileobj.close()
    def fileno(self):
        return self.fileobj.fileno()
    
    def _get_read_overlapped(self):
        return win32file.OVERLAPPED()
    def _get_write_overlapped(self):
        return win32file.OVERLAPPED()
    
    def read(self, count):
        count = min(count, self.MAX_READ_SIZE)
        
        def finished(size, overlapped):
            self._keepalive.pop(overlapped)
            data = str(buf[:size])
            self.reactor.call(dfr.set, data)
        
        dfr = Deferred()
        try:
            overlapped = self._get_read_overlapped()
            buf = win32file.AllocateReadBuffer(count)
            win32file.ReadFile(self.fileno(), buf, overlapped)
        except Exception as ex:
            dfr.throw(ex)
        else:
            overlapped.object = finished
            self._keepalive[overlapped] = finished
        return dfr
    
    def write(self, data):
        remaining = [data]
        
        def write_more():
            if not remaining[0]:
                self.reactor.call(dfr.set)
                return
            chunk = remaining[0][:self.MAX_WRITE_SIZE]
            try:
                overlapped = self._get_write_overlapped()
                win32file.WriteFile(self.fileno(), chunk, overlapped)
            except Exception as ex:
                self.reactor.call(dfr.throw, ex)
            else:
                overlapped.object = finished
                self._keepalive[overlapped] = finished
        
        def finished(size, overlapped):
            self._keepalive.pop(overlapped)
            remaining[0] = remaining[0][size:]
            if not remaining[0]:
                self.reactor.call(dfr.set)
            else:
                write_more()

        dfr = Deferred()
        write_more()
        return dfr
    



