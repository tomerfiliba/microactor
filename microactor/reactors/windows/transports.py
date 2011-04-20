import socket
from microactor.utils import safe_import, ReactorDeferred, reactive
from ..transports import ClosedFile, DetachedFile
from ..transports import OverlappingRequestError 
msvcrt = safe_import("msvcrt")
win32file = safe_import("win32file")
win32iocp = safe_import("microactor.arch.windows.iocp")
pywintypes = safe_import("pywintypes")


class BaseTransport(object):
    __slots__ = ["reactor"]
    def __init__(self, reactor):
        self.reactor = reactor
    def _register(self):
        self.reactor.register_transport(self)
    def detach(self):
        raise NotImplementedError()
    def close(self):
        raise NotImplementedError()
    def fileno(self):
        raise NotImplementedError()

    def on_error(self, exc):
        pass


class StreamTransport(BaseTransport):
    MAX_READ_SIZE = 32000
    MAX_WRITE_SIZE = 32000
    
    __slots__ = ["fileobj", "_ongoing_read", "_ongoing_write"]
    def __init__(self, reactor, fileobj):
        BaseTransport.__init__(self, reactor)
        self.fileobj = fileobj
        self._register()
        self._ongoing_read = False
        self._ongoing_write = False
    
    def fileno(self):
        return msvcrt.get_osfhandle(self.fileobj.fileno())
    def detach(self):
        if self.fileobj:
            self.reactor._detach(self)
            self.fileobj = DetachedFile
    def close(self):
        if self.fileobj:
            self.reactor._detach(self)
            self.fileobj.close()
            self.fileobj = ClosedFile
    
    def read(self, count):
        if self._ongoing_read:
            raise OverlappingRequestError("overlapping reads")
        self._ongoing_read = True
        
        def read_finished(size, _):
            data = str(buf[:size])
            self._ongoing_read = False
            dfr.set(data)
        
        dfr = ReactorDeferred(self.reactor)
        count = min(count, self.MAX_READ_SIZE)
        overlapped = self.reactor._get_overlapped(read_finished)
        try:
            buf = win32file.AllocateReadBuffer(count)
            win32file.ReadFile(self.fileno(), buf, overlapped)
        except Exception as ex:
            self.reactor._discard_overlapped(overlapped)
            self._ongoing_read = False
            if isinstance(ex, pywintypes.error) and ex.winerror in win32iocp.BROKEN_PIPE_ERRORS:
                # why can't windows be just a little consistent?! 
                # why can't a set of APIs have the same semantics for all kinds
                # of handles? grrrrr
                dfr.set(None)
            else:
                dfr.throw(ex)
        return dfr
    
    def write(self, data):
        if self._ongoing_write:
            raise OverlappingRequestError("overlapping writes")

        self._ongoing_write = True
        remaining = [data]
        
        def write_finished(size, _):
            remaining[0] = remaining[0][:size]
            if not remaining[0]:
                self._ongoing_write = False
                dfr.set()
            else:
                write_some()
        
        def write_some():
            if not remaining[0]:
                self._ongoing_write = False
                dfr.set()
                return
            chunk = remaining[0][:self.MAX_READ_SIZE]
            overlapped = self.reactor._get_overlapped(write_finished)
            print "write_some", repr(chunk), overlapped
            try:
                win32file.WriteFile(self.fileno(), chunk, overlapped)
            except Exception as ex:
                self._ongoing_write = False
                self.reactor._discard_overlapped(overlapped)
                dfr.throw(ex)
        
        dfr = ReactorDeferred(self.reactor)
        write_some()
        return dfr


class SocketStreamTransport(StreamTransport):
    __slots__ = []
    def __init__(self, reactor, sock):
        StreamTransport.__init__(self, reactor, sock)
        sock.setblocking(False)
    
    def fileno(self):
        return self.fileobj.fileno() # no need to translate with get_osfhandle
    def getsockname(self):
        return self.fileobj.getsockname()
    def getpeername(self):
        return self.fileobj.getpeername()
    
    def close(self):
        try:
            self.shutdown()
        except EnvironmentError:
            pass
        StreamTransport.close(self)

    def shutdown(self, mode = "rw"):
        if mode == "r":
            flags = socket.SHUT_RD
        elif mode == "w":
            flags = socket.SHUT_WR
        elif mode == "rw":
            flags = socket.SHUT_RDWR
        else:
            raise ValueError("invalid mode: %r" % (mode,))
        self.fileobj.shutdown(flags)


class PipeTransport(StreamTransport):
    def __init__(self, reactor, fileobj, mode, auto_flush = True):
        if mode not in ["r", "w", "rw"]:
            raise ValueError("mode must be 'r', 'w', or 'rw'")
        self.mode = mode
        self.name = getattr(fileobj, "name", None)
        self.auto_flush = auto_flush
        StreamTransport.__init__(self, reactor, fileobj)
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
    pass


class BaseSocketTransport(BaseTransport):
    __slots__ = ["sock"]
    def __init__(self, reactor, sock):
        BaseTransport.__init__(self, reactor)
        self.sock.setblocking(False)
    def fileno(self):
        return self.sock.fileno() # no need to translate with get_osfhandle
    def detach(self):
        if self.sock:
            self.reactor._detach(self)
            self.sock = DetachedFile
    def close(self):
        if self.sock:
            self.reactor._detach(self)
            self.sock.close()
            self.sock = ClosedFile


class ListeningSocketTransport(BaseSocketTransport):
    __slots__ = ["factory"]
    def __init__(self, reactor, sock, factory = SocketStreamTransport):
        BaseSocketTransport.__init__(self, reactor, sock)
        self.factory = factory
        self._register()

    def getsockname(self):
        return self.sock.getsockname()
    
    def accept(self):
        def accept_finished(size, _):
            dfr.set(trns)
        
        dfr = ReactorDeferred(self.reactor)
        # this is needed here to register the new socket with its IOCP
        overlapped = self.reactor._get_overlapped(accept_finished)
        try:
            sock = socket.socket(self.sock.family, self.sock.type)
            trns = self.factory(self.reactor, sock)
            fd = sock.fileno()
            buffer = win32file.AllocateReadBuffer(win32file.CalculateSocketEndPointSize(fd))
            win32file.AcceptEx(self.fileno(), fd, buffer, overlapped)
        except Exception as ex:
            self.reactor._discard_overlapped(overlapped)
            dfr.throw(ex)
        return dfr





