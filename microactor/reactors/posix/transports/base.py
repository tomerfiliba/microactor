from microactor.utils import Deferred
from microactor.lib import Queue
from io import BytesIO


class BaseTransport(object):
    __slots__ = ["reactor"]
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
    __slots__ = ["fileobj", "write_queue", "read_queue"]
    
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
        self.read_queue.push((dfr, count))
        self.reactor.register_read(self)
        return dfr

    def on_read(self, hint):
        if hint < 0:
            hint = self.READ_SIZE
        dfr, count = self.read_queue.pop()
        try:
            data = self._do_read(min(count, hint))
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(data)
        
        if not self.read_queue:
            self.reactor.unregister_read(self)

    def _do_read(self, count):
        return self.fileobj.read(count)

    def on_write(self, hint):
        if hint < 0:
            hint = self.WRITE_SIZE
        dfr, stream, size = self.write_queue.pop()
        data = stream.read(hint)
        try:
            written = self._do_write(data)
        except Exception as ex:
            dfr.throw(ex)
        else:
            if written is not None:
                stream.seek(written - len(data), 1)
            if stream.tell() >= size:
                dfr.set()
        if not self.write_queue:
            self.reactor.unregister_write(self)

    def _do_write(self, count):
        return self.fileobj.write(count)









