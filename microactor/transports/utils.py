from .base import WrappedStreamTransport
from microactor.utils import reactive, rreturn, Deferred
from microactor.lib import Queue



class BufferedTransport(WrappedStreamTransport):
    def __init__(self, transport, read_buffer_size = 16000, write_buffer_size = 16000):
        WrappedStreamTransport.__init__(self, transport)
        self._rbufsize = read_buffer_size
        self._wbufsize = write_buffer_size
        self._rbuf = ""
        self._wbuf = ""

    @reactive
    def close(self):
        yield self.flush()
        yield self.transport.close()

    @reactive
    def _fill_rbuf(self, count):
        while count > 0:
            data = yield self.transport.read(count)
            if not data:
                rreturn(True)
            self._rbuf += data
            if len(data) < count:
                break
            count -= len(data)
        rreturn(False)
    
    @reactive
    def read(self, count):
        if count > len(self._rbuf):
            yield self._fill_rbuf(self._read_buffer_size - len(self._rbuf))

        data = self._rbuf[:count]
        self._rbuf = self._rbuf[count:]
        rreturn(data)
    
    @reactive
    def read_all(self, chunk = 16000):
        while True:
            data = yield self.transport.read(chunk)
            if not data:
                break
            self._rbuf += data
        data = self._rbuf
        self._rbuf = ""
        rreturn(data)
    
    @reactive
    def read_until(self, pattern, raise_on_eof = False):
        eof = False
        last_index = 0
        while True:
            ind = self._rbuf.find(pattern, last_index)
            if ind >= 0:
                data = self._rbuf[:ind]
                self._rbuf = self._rbuf[ind + len(pattern):]
                rreturn(data)
            else:
                if eof:
                    if raise_on_eof:
                        raise EOFError()
                    else:
                        data = self._rbuf
                        self._rbuf = ""
                        rreturn(data)
                eof = yield self._fill_rbuf(self._rbufsize)
                last_index = len(self._rbuf) - len(pattern)
    
    def read_line(self):
        return self.read_until("\n")
    
    @reactive
    def _empty_wbuf(self):
        yield self.transport.write(self._wbuf)
        self._wbuf = ""
    
    @reactive
    def flush(self):
        yield self._empty_wbuf()
    
    @reactive
    def write(self, data):
        self._wbuf += data
        if len(self._wbuf) > self._wbufsize:
            yield self._empty_wbuf()
    
    
class BoundTransport(WrappedStreamTransport):
    def __init__(self, transport, read_length, write_length):
        WrappedStreamTransport.__init__(self, transport)
        self._rlength = read_length
        self._wlength = write_length
    
    def remaining_read(self):
        return self._rlength

    def remaining_write(self):
        return self._wlength
    
    @reactive
    def read(self, count):
        if self._rlength is None:
            data = yield self.transport.read(count)
            rreturn(data)
        if self._rlength <= 0:
            rreturn("")
        count = min(count, self._rlength)
        data = yield self.transport.read(count)
        self._rlength -= len(data)
        rreturn(data)

    @reactive
    def write(self, data):
        if self._wlength is None:
            yield self.transport.write(data)
        elif len(data) > self._wlength:
            raise EOFError("stream ended")
        else:
            yield self.transport.write(data)
            self._wlength -= len(data)


class Transactional(object):
    def __init__(self, underlying):
        self.queue = Queue()
        self.underlying = underlying
    
    @reactive
    def __enter__(self):
        rreturn(self.begin())

    @reactive
    def __exit__(self):
        self.end()
    
    def begin(self):
        dfr = Deferred()
        self.queue.push(dfr)
        if len(self.queue) == 1:
            dfr.set(self.underlying)
        return dfr

    def end(self):
        self.queue.pop()
        if self.queue:
            dfr = self.queue.peek()
            dfr.set(self.underlying)







