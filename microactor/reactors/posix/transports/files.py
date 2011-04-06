from microactor.transports.base import StreamTransport
from microactor.utils import Deferred


class PipeTransport(StreamTransport):
    def __init__(self, reactor, fileobj, mode, auto_flush = True):
        self.mode = mode
        if self.mode not in ["r", "w", "rw"]:
            raise ValueError("mode must be 'r', 'w', or 'rw'")
        self.auto_flush = auto_flush
        StreamTransport.__init__(self, reactor, fileobj)
        if "w" not in self.mode:
            def write(data):
                raise IOError("file mode does not allow for writing")
            self.write = write
            self.flush = write
    
    def flush(self):
        dfr = Deferred()
        return dfr

    def _do_write(self, data):
        StreamTransport._do_write(self, data)
        if self.auto_flush:
            self.fileobj.flush()

class FileTransport(StreamTransport):
    def __init__(self, reactor, fileobj):
        StreamTransport.__init__(self, reactor, fileobj)
    
    def seek(self, offset, whence = 0):
        self.fileobj.seek(offset, whence)
    
    def tell(self):
        return self.fileobj.tell()

    def isatty(self):
        return self.fileobj.isatty()
