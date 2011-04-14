import sys
import socket
import os
from microactor.utils import Deferred
from microactor.utils.colls import Queue
from io import BytesIO



class TransportError(Exception):
    pass
class NeedMoreData(TransportError):
    pass

class BaseTransport(object):
    __slots__ = ["reactor"]
    def __init__(self, reactor):
        self.reactor = reactor
    def _unregister(self):
        self.reactor.unregister_read(self)
        self.reactor.unregister_write(self)
    def detach(self):
        raise NotImplementedError()
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
    __slots__ = ["fileobj", "_write_queue", "_read_queue", "_eof"]
    
    def __init__(self, reactor, fileobj):
        BaseTransport.__init__(self, reactor)
        self.fileobj = fileobj
        self._write_queue = Queue()
        self._read_queue = Queue()
        self._eof = False
    def detach(self):
        self._unregister()
        self.fileobj = None
    def close(self):
        if not self.fileobj:
            return
        self._unregister()
        self.fileobj.close()
        self.fileobj = None
    def fileno(self):
        if not self.fileobj:
            raise TransportError("stale transport")
        return self.fileobj.fileno()
    
    def write(self, data):
        if not self.fileobj:
            raise TransportError("stale transport")
        dfr = Deferred(self.reactor)
        self._write_queue.push((dfr, BytesIO(data), len(data)))
        self.reactor.register_write(self)
        return dfr
    
    def read(self, count):
        if not self.fileobj:
            raise TransportError("stale transport")
        if self._eof:
            return Deferred(self.reactor, "")
        dfr = Deferred(self.reactor)
        self._read_queue.push((dfr, count))
        self.reactor.register_read(self)
        return dfr

    def on_read(self, hint):
        if hint < 0:
            hint = self.READ_SIZE
        dfr, count = self._read_queue.peek()
        try:
            data = self._do_read(min(count, hint))
        except NeedMoreData:
            # don't pop from _read_queue
            pass
        except Exception as ex:
            self._read_queue.pop()
            dfr.throw(ex)
        else:
            self._read_queue.pop()
            dfr.set(data)
            if not data:
                self._eof = True
                while self._read_queue:
                    dfr, _ = self._read_queue.pop()
                    dfr.set("")
        
        if not self._read_queue or self._eof:
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


class PipeWakeupTransport(BaseTransport):
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
        os.read(self._rfd, 100)
        self._is_set = False

    def is_set(self):
        return self._is_set
    
    def on_read(self, hint):
        if self.auto_reset:
            self.reset()


class SocketWakeupTransport(BaseTransport):
    def __init__(self, reactor, auto_reset = True):
        BaseTransport.__init__(self, reactor)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("localhost", 0))
        listener.listen(1)
        self.wsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.wsock.connect(listener.getsockname())
        self.rsock, _ = listener.accept()
        listener.close()
        self._is_set = False
        self.auto_reset = auto_reset
    
    def close(self):
        if self.rsock is None:
            return
        self.rsock.close()
        self.wsock.close()
        self.rsock = None
        self.wsock = None
    
    def fileno(self):
        return self.rsock.fileno()
    
    def set(self):
        if self._is_set:
            return
        self._is_set = True
        self.wsock.send("x")
    
    def reset(self):
        if not self._is_set:
            return
        self.rsock.recv(100)
        self._is_set = False

    def is_set(self):
        return self._is_set
    
    def on_read(self, hint):
        if self.auto_reset:
            self.reset()

if sys.platform == "win32":
    WakeupTransport = SocketWakeupTransport
else:
    WakeupTransport = PipeWakeupTransport





