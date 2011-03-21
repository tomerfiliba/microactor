from microactor.utils import Deferred
from microactor.lib import Queue
from io import BytesIO


class BaseTransport(object):
    def __init__(self, reactor):
        self.reactor = reactor
    def _unregister(self):
        self.reactor.unregister_read(self)
        self.reactor.unregister_write(self)
    def close(self):
        raise NotImplementedError()
    def fileno(self):
        raise NotImplementedError()

    def on_read(self, hint):
        raise NotImplementedError()
    def on_write(self, hint):
        raise NotImplementedError()
    def on_error(self, info):
        pass


class StreamTransport(BaseTransport):
    WRITE_SIZE = 16000
    READ_SIZE = 16000
    
    def __init__(self, reactor, fileobj):
        BaseTransport.__init__(self, reactor)
        self.fileobj = fileobj
        self.write_queue = Queue()
        self.read_queue = Queue()
    def close(self):
        self._unregister()
        self.fileobj.close()
    def fileno(self):
        return self.fileobj.fileno()
    
    def write(self, data):
        dfr = Deferred()
        self.write_queue.push((dfr, BytesIO(data), len(data)))
        self.reactor.register_write(self)
        return dfr
    
    def read(self, count):
        dfr = Deferred()
        self.read_queue.push((dfr, count, None))
        self.reactor.register_read(self)
        return dfr

    def readn(self, count):
        dfr = Deferred()
        self.read_queue.push((dfr, count, ""))
        self.reactor.register_read(self)
        return dfr
    
    def on_read(self, hint):
        if hint < 0:
            hint = self.READ_SIZE
        dfr, count, buffer = slot = self.read_queue.peek()
        data = self._do_read(min(count, hint))
        if buffer is None:
            self.read_queue.pop()
            if data:
                dfr.set(data)
            else:
                dfr.throw(EOFError())
        else:
            count -= len(data)
            buffer += data
            if not data or count <= 0:
                self.read_queue.pop()
                if buffer:
                    dfr.set(buffer)
                else:
                    dfr.throw(EOFError())
            else:
                slot[1] = count
                slot[2] = buffer
        
        if not self.read_queue:
            self.reactor.unregister_read(self)

    def _do_read(self, count):
        return self.fileobj.read(count)

    def on_write(self, hint):
        if hint < 0:
            hint = self.WRITE_SIZE
        dfr, stream, size = self.write_queue.pop()
        data = stream.read(hint)
        written = self._do_write(data)
        if written is not None:
            stream.seek(written - len(data), 1)
        if stream.tell() >= size:
            dfr.set()
        if not self.write_queue:
            self.reactor.unregister_write(self)

    def _do_write(self, count):
        return self.fileobj.write(count)








