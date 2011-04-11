from .base import StreamTransport
from microactor.utils import Deferred, reactive, safe_import
win32file = safe_import("win32file")


class PipeTransport(StreamTransport):
    def __init__(self, reactor, fileobj, mode, auto_flush = True):
        self.mode = mode
        self.name = getattr(fileobj, "name", None)
        if self.mode not in ["r", "w", "rw"]:
            raise ValueError("mode must be 'r', 'w', or 'rw'")
        self.auto_flush = auto_flush
        if "r" not in self.mode:
            self.read = self._wrong_mode
        if "w" not in self.mode:
            self.write = self._wrong_mode
            self.flush = self._wrong_mode

    @staticmethod
    def _wrong_mode(*args):
        raise IOError("file mode does not permit this operation")

    def flush(self):
        win32file.FlushFileBuffers(self.fileno())
    def isatty(self):
        return self.fileobj.isatty()

    @reactive
    def write(self, data):
        yield StreamTransport.write(self, data)
        if self.auto_flush:
            yield self.flush()


class FileTransport(StreamTransport):
    def flush(self):
        win32file.FlushFileBuffers(self.fileno())
    def isatty(self):
        return self.fileobj.isatty()
    def seek(self, offset, whence = 0):
        self.fileobj.seek(offset, whence)
    def tell(self):
        return self.fileobj.tell()
    def _get_read_overlapped(self):
        overlapped = win32file.OVERLAPPED()
        overlapped.Offset = self.tell()
        return overlapped
    def _get_write_overlapped(self):
        overlapped = win32file.OVERLAPPED()
        overlapped.Offset = self.tell()
        return overlapped







