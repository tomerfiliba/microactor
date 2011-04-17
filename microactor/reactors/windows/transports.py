import socket
from microactor.utils import safe_import, ReactorDeferred
from ..transports import ClosedFile, DetachedFile
from ..transports import TransportError, ReadRequiresMoreData, OverlappingRequestError 
win32file = safe_import("win32file")


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
    
    __slots__ = ["fileobj"]
    def __init__(self, reactor, fileobj):
        BaseTransport.__init__(self, reactor)
        self.fileobj = fileobj
        self._register()
    
    def fileno(self):
        return self.fileobj.fileno()
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
        def read_finished(size, _):
            data = str(buf[:size])
            dfr.set(data)
        
        dfr = ReactorDeferred(self.reactor)
        count = min(count, self.MAX_READ_SIZE)
        overlapped = self.reactor._get_overlapped(read_finished)
        try:
            buf = win32file.AllocateReadBuffer(count)
            win32file.ReadFile(self.fileno(), buf, overlapped)
        except Exception as ex:
            self.reactor._discard_overlapped(overlapped)
            dfr.throw(ex)
        return dfr
    
    def write(self, data):
        remaining = [data]
        
        def write_finished(size, _):
            remaining[0] = remaining[0][:size]
            if not remaining[0]:
                dfr.set()
            else:
                write_some()
        
        def write_some():
            if not remaining[0]:
                dfr.set()
                return
            chunk = remaining[0][:self.MAX_READ_SIZE]
            overlapped = self.reactor._get_overlapped(write_finished)
            print "write_some", repr(chunk), overlapped
            try:
                win32file.WriteFile(self.fileno(), chunk, overlapped)
            except Exception as ex:
                print ex
                self.reactor._discard_overlapped(overlapped)
                dfr.throw(ex)
        
        dfr = ReactorDeferred(self.reactor)
        write_some()
        return dfr


class SocketStreamTransport(StreamTransport):
    def __init__(self, reactor, sock):
        StreamTransport.__init__(self, reactor, sock)
        sock.setblocking(False)
    
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


class BaseSocketTransport(BaseTransport):
    __slots__ = ["sock"]
    def __init__(self, reactor, sock):
        BaseTransport.__init__(self, reactor)
        self.sock.setblocking(False)
    def fileno(self):
        return self.sock.fileno()
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





