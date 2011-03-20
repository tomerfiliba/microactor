import socket
import os
import weakref
try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO


class Deferred(object):
    __slots__ = ["_callbacks", "value"]
    def __init__(self, value = NotImplemented):
        self.value = value
        self._callbacks = []
    def register(self, cb):
        if self.value is NotImplemented:
            self._callbacks.append(cb)
        else:
            cb(self.value)
    def set(self, value = None):
        if self.value is not NotImplemented:
            raise ValueError("Deferred has already been set")
        self.value = value
        for cb in self._callbacks:
            cb(self.value)
        del self._callbacks


class BaseTransport(object):
    __slots__ = ["reactor"]
    def __init__(self, reactor):
        self.reactor = weakref.proxy(reactor)
    def close(self):
        self.reactor.unregister_transport(self, "rw")
    def fileno(self):
        raise NotImplementedError()
    def on_read(self, hint = -1):
        raise NotImplementedError()
    def on_write(self, hint = -1):
        raise NotImplementedError()
    def on_error(self, info):
        pass


class StreamTransport(BaseTransport):
    WRITE_SIZE = 16000
    READ_SIZE = 16000
    
    def __init__(self, reactor, fileobj):
        self.fileobj = fileobj
        self.read_size = self.READ_SIZE
        self.write_size = self.WRITE_SIZE
        self.read_queue = []
        self.write_queue = []

    def close(self):
        BaseTransport.close(self)
        self.fileobj.close()
    
    def read(self, count):
        self.reactor.register_transport(self, "r")
        d = Deferred()
        self.read_queue.append(d)
        return d
    
    def write(self, data):
        self.reactor.register_transport(self, "w")
        d = Deferred(BytesIO(data))
        self.write_queue.append(d)
        return d
    
    def on_read(self, hint = -1):
        if hint < 0:
            hint = self.read_size
        data = self.fileobj.read(hint)
        dfr = self.read_queue.pop(-1)
        dfr.set(data)
        if not self.read_queue:
            self.reactor.unregister_transport(self, "r")
    
    def on_write(self, hint = -1):
        if hint < 0:
            hint = self.write_size
        dfr = self.write_queue[0]
        
        data = dfr.data[:hint]
        dfr.data = dfr.data[hint:]
        self.fileobj.write(data)
        if not dfr.data:
            self.write_queue.pop(0)
            dfr.set(None)
        if not self.write_queue:
            self.reactor.unregister_transport(self, "w")


class TcpStreamTransport(StreamTransport):
    pass

class TcpListenerTransport(BaseTransport):
    def __init__(self, reactor, sock):
        BaseTransport.__init__(self, reactor)
        self.sock = sock
        self.accept_queue = []
    def accept(self):
        self.reactor.register_transport(self, "r")
        dfr = Deferred()
        self.accept_queue.append(dfr)
        return dfr
    def on_read(self):
        dfr = self.accept_queue.pop(0)
        s, _ = self.sock.accept()
        trns = TcpStreamTransport(self.reactor, s)
        dfr.set(trns)
        if not self.accept_queue:
            self.reactor.unregister_transport(self, "r")

class Subsystem(object):
    def __init__(self, reactor):
        self.reactor = reactor
        self._init()
    def _init(self):
        pass

class TcpSubsystem(Subsystem):
    def connect(self, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        trns = TcpStreamTransport(self.reactor, s)
        dfr = Deferred()
        
        """
        from asyncore: select for writing
        
        def connect(self, address):
            self.connected = False
            err = self.socket.connect_ex(address)
            if err in (EINPROGRESS, EALREADY, EWOULDBLOCK)  or err == EINVAL and os.name in ('nt', 'ce'):
                return
            if err in (0, EISCONN):
                self.addr = address
                self.handle_connect_event()
            else:
                raise socket.error(err, errorcode[err])
        """
        
        self.reactor.register_transport(trns, "w")
        
        err = s.connect_ex((host, port))
        
        
        dfr.set(TcpStreamTransport(self.reactor, s))
        return dfr
    def listen(self, port, host = "0.0.0.0", backlog = 10):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, port))
        s.listen(backlog)
        return Deferred(TcpListenerTransport(self.reactor, s))

class ReactiveReturn(Exception):
    def __init__(self, value):
        self.value = value

def rreturn(value = None):
    raise ReactiveReturn(value)

def reactive(func):
    def wrapper(*args, **kwargs):
        def continuation(res):
            try:
                dfr2 = gen.send(res)
            except ReactiveReturn as ex:
                retval.set(ex.value)
            except StopIteration:
                retval.set(None)
            else:
                dfr2.register(continuation)
        
        retval = Deferred()
        try:
            gen = func(*args, **kwargs)
        except ReactiveReturn as ex:
            retval.set(ex.value)
        except StopIteration:
            retval.set(None)
        else:
            continuation(None)
        return retval
    return wrapper






