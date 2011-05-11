from io import BytesIO
from .deferred import reactive, rreturn
import struct


class Packer(object):
    __slots__ = []
    @reactive
    def unpack(self, stream):
        raise NotImplementedError()
    @reactive
    def pack(self, obj, stream):
        raise NotImplementedError()

class Primitive(Packer):
    __slots__ = ["packer"]
    def __init__(self, format):
        self.packer = struct.Struct(format)
    @reactive
    def unpack(self, stream):
        data = yield stream.read(self.packer.size)
        rreturn (self.packer.unpack(data)[0])
    @reactive
    def pack(self, obj, stream):
        yield stream.write(self.packer.pack(obj))

int8_s = Primitive("b")
int8_u = Primitive("B")

int16_sb = Primitive(">h")
int16_sl = Primitive("<h")
int16_sn = Primitive("=h")
int16_ub = Primitive(">H")
int16_ul = Primitive("<H")
int16_un = Primitive("=H")

int32_sb = Primitive(">l")
int32_sl = Primitive("<l")
int32_sn = Primitive("=l")
int32_ub = Primitive(">L")
int32_ul = Primitive("<L")
int32_un = Primitive("=L")

int64_sb = Primitive(">q")
int64_sl = Primitive("<q")
int64_sn = Primitive("=q")
int64_ub = Primitive(">Q")
int64_ul = Primitive("<Q")
int64_un = Primitive("=Q")

float32_b = Primitive(">f")
float32_l = Primitive("<f")
float32_n = Primitive("=f")
float64_b = Primitive(">d")
float64_l = Primitive("<d")
float64_n = Primitive("=d")

class Buffer(Packer):
    __slots__ = ["length"]
    def __init__(self, length):
        self.length = length
    @reactive
    def unpack(self, stream):
        data = yield stream.read(self.length)
        if len(data) != self.length:
            raise EOFError()
        rreturn (data)
    @reactive
    def pack(self, data, stream):
        if len(data) != self.length:
            raise ValueError("wrong length")
        yield stream.write(data)


class FramedTransport(object):
    def __init__(self, transport):
        self.transport = transport
    
    @reactive
    def read(self):
        length = yield int32_ub.unpack(self.transport)
        data = yield self.transport.read(length)
        rreturn (data)

    @reactive
    def write(self, data):
        yield int32_ub.pack(len(data))
        yield self.transport.write(data)




