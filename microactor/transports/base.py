from microactor.utils import Deferred, reactive, rreturn
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
        self.read_queue.push((dfr, count))
        self.reactor.register_read(self)
        return dfr

    @reactive
    def readn(self, count, raise_on_eof = False):
        buffer = []
        while count > 0:
            data = yield self.read(count)
            if not data:
                break
            count -= len(data)
            buffer.append(data)
        data = "".join(buffer)
        if raise_on_eof and count > 0:
            raise EOFError()
        rreturn(data)
    
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


class WrappedStreamTransport(StreamTransport):
    def __init__(self, transport):
        BaseTransport.__init__(self, transport.reactor)
        self.transport = transport
    def fileno(self):
        # this is a slot method, doesn't go through __getattr__
        return self.transport.fileno()
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.transport, name)






