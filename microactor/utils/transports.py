from .deferred import reactive, rreturn
import sys
import codecs


class StreamTransportAdapter(object):
    __slots__ = ["transport", "reactor"]
    
    def __init__(self, transport):
        self.reactor = transport.reactor
        self.transport = transport
    
    def close(self):
        return self.transport.close()
    def detach(self):
        return self.transport.detach()
    def fileno(self):
        return self.transport.fileno()
    def write(self, data):
        return self.transport.write(data)
    def read(self, count):
        return self.transport.read(count)


class CodecTransport(StreamTransportAdapter):
    def __init__(self, transport, encoding = None, errors = "strict"):
        StreamTransportAdapter.__init__(self, transport)
        if encoding is None:
            encoding = sys.getfilesystemencoding()
        self.encoding = encoding
        self.encoder = codecs.getincrementalencoder(encoding)(errors)
        self.decoder = codecs.getincrementaldecoder(encoding)(errors)
    
    @reactive
    def close(self):
        raw = self.encoder.encode("", final = True)
        if raw:
            yield self.transport.write(raw)
        yield self.transport.close()
    
    @reactive
    def read(self, count):
        raw = yield self.transport.read(count)
        if raw is None:
            rreturn(self.decoder.decode("", final = True))
        else:
            rreturn(self.decoder.decode(raw))
    
    @reactive
    def write(self, data):
        raw = self.encoder.encode(data)
        if raw:
            yield self.transport.write(raw)


class BufferedTransport(StreamTransportAdapter):
    def __init__(self, transport, read_buffer_size = 16000, write_buffer_size = 16000):
        StreamTransportAdapter.__init__(self, transport)
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
        if count < 0:
            data = yield self.read_all()
            rreturn(data)
        if count > len(self._rbuf):
            yield self._fill_rbuf(self._read_buffer_size - len(self._rbuf))

        data = self._rbuf[:count]
        self._rbuf = self._rbuf[count:]
        rreturn(data)

    @reactive
    def read_exactly(self, count, raise_on_eof = True):
        buffer = []
        orig_count = count
        while count > 0:
            data = yield self.read(count)
            if not data:
                break
            count -= len(data)
            buffer.append(data)
        data = "".join(buffer)
        if raise_on_eof and count > 0:
            raise EOFError("requested %r bytes, got %r" % (orig_count, len(data)), data)
        rreturn(data)
    
    @reactive
    def read_all(self, chunk = 16000):
        chunks = [self._rbuf]
        self._rbuf = ""
        while True:
            data = yield self.transport.read(chunk)
            if not data:
                break
            chunks.append(data)
        rreturn("".join(chunks))
    
    @reactive
    def read_until(self, patterns, raise_on_eof = False, include_pattern = False):
        if isinstance(patterns, str):
            patterns = [patterns]
        longest_pattern = max(len(p) for p in patterns)
        eof = False
        last_index = 0
        while True:
            for pat in patterns:
                ind = self._rbuf.find(pat, last_index)
                if ind >= 0:
                    if include_pattern:
                        data = self._rbuf[:ind + len(pat)]
                    else:
                        data = self._rbuf[:ind]
                    self._rbuf = self._rbuf[ind + len(pat):]
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
                last_index = len(self._rbuf) - longest_pattern
    
    def read_line(self):
        return self.read_until(("\r\n", "\r", "\n"))
    
    @reactive
    def flush(self):
        data = self._wbuf
        self._wbuf = ""
        yield self.transport.write(data)
        if hasattr(self.transport, "flush"):
            yield self.transport.flush()
    
    @reactive
    def write(self, data):
        self._wbuf += data
        if len(self._wbuf) > self._wbufsize:
            yield self.flush()


class BoundTransport(StreamTransportAdapter):
    def __init__(self, transport, read_length, write_length, skip_on_close = True, close_underlying = True):
        StreamTransportAdapter.__init__(self, transport)
        self._rlength = read_length
        self._wlength = write_length
        self.skip_on_close = skip_on_close
        self.close_underlying = close_underlying
    
    @reactive
    def close(self):
        if self.skip_on_close:
            yield self.skip()
        if self.close_underlying:
            yield self.transport.close()
    
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
    def skip(self, count = -1):
        if count < 0:
            count = self._rlength
        actually_read = 0
        while count > 0:
            data = yield self.read(count)
            if not data:
                break
            actually_read += len(data)
            count -= len(data)
        rreturn(actually_read)

    @reactive
    def write(self, data):
        if self._wlength is None:
            yield self.transport.write(data)
        elif len(data) > self._wlength:
            raise EOFError("stream ended")
        else:
            yield self.transport.write(data)
            self._wlength -= len(data)


