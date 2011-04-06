import os
from microactor.utils import Deferred
from microactor.utils.colls import Queue
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
    __slots__ = ["fileobj", "_write_queue", "_read_queue"]
    
    def __init__(self, reactor, fileobj):
        BaseTransport.__init__(self, reactor)
        self.fileobj = fileobj
        self._write_queue = Queue()
        self._read_queue = Queue()
    def close(self):
        self._unregister()
        self.fileobj.close()
    def fileno(self):
        return self.fileobj.fileno()
    
    def write(self, data):
        dfr = Deferred()
        self._write_queue.push((dfr, BytesIO(data), len(data)))
        self.reactor.register_write(self)
        return dfr
    
    def read(self, count):
        dfr = Deferred()
        self._read_queue.push((dfr, count))
        self.reactor.register_read(self)
        return dfr

    def on_read(self, hint):
        if hint < 0:
            hint = self.READ_SIZE
        dfr, count = self._read_queue.pop()
        try:
            data = self._do_read(min(count, hint))
        except Exception as ex:
            dfr.throw(ex)
        else:
            dfr.set(data)
        
        if not self._read_queue:
            self.reactor.unregister_read(self)

    def _do_read(self, count):
        return self.fileobj.read(count)

    def on_write(self, hint):
        if hint < 0:
            hint = self.WRITE_SIZE
        dfr, stream, size = self._write_queue.pop()
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
        if not self._write_queue:
            self.reactor.unregister_write(self)

    def _do_write(self, count):
        return self.fileobj.write(count)


class EventTransport(BaseTransport):
    def __init__(self, reactor, auto_reset = True):
        BaseTransport.__init__(self, reactor)
        self._rfd, self._wfd = os.pipe()
        self._is_set = False
        self.auto_reset = auto_reset
    
    def close(self):
        if self._rfd is None:
            return
        os.close(self._rfd)
        os.close(self._wfd)
        self._rfd = None
        self._wfd = None
    
    def fileno(self):
        return self._rfd
    
    def set(self):
        if self._is_set:
            return
        self._is_set = True
        os.write(self._wfd, "x")
    
    def reset(self):
        if not self._is_set:
            return
        os.read(self._rds, 100)
        self._is_set = False

    def is_set(self):
        return self._is_set
    
    def on_read(self, hint):
        if self.auto_reset:
            self.reset()









