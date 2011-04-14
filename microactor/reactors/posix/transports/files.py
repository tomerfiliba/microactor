import os
from .base import StreamTransport
from microactor.utils import safe_import
from microactor.utils.deferred import Deferred
fcntl = safe_import("fcntl")


class PipeTransport(StreamTransport):
    def __init__(self, reactor, fileobj, mode, auto_flush = True):
        self.mode = mode
        self.name = getattr(fileobj, "name", None)
        if self.mode not in ["r", "w", "rw"]:
            raise ValueError("mode must be 'r', 'w', or 'rw'")
        self.auto_flush = auto_flush
        self._flush_dfr = None
        self._unblock(fileobj.fileno())
        StreamTransport.__init__(self, reactor, fileobj)
        if "r" not in self.mode:
            self.read = self._wrong_mode
        if "w" not in self.mode:
            self.write = self._wrong_mode
            self.flush = self._wrong_mode

    @staticmethod
    def _wrong_mode(*args):
        raise IOError("file mode does not permit this operation")

    @classmethod
    def _unblock(cls, fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    
    def flush(self):
        if self._flush_dfr is None:
            self._flush_dfr = Deferred()
            self.reactor.register_write(self)
        return self._flush_dfr

    def isatty(self):
        return self.fileobj.isatty()

    def _do_write(self, data):
        StreamTransport._do_write(self, data)
        if self.auto_flush or self._flush_dfr:
            self.fileobj.flush()
            self.reactor.call(self._flush_dfr.set)
            self._flush_dfr = None


class FileTransport(PipeTransport):
    def seek(self, offset, whence = 0):
        self.fileobj.seek(offset, whence)
    def tell(self):
        return self.fileobj.tell()


