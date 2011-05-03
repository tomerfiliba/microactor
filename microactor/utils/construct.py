from struct import Struct as _Struct
from io import BytesIO
from collections import OrderedDict
from types import GeneratorType


class Construct(object):
    __slots__ = []
    def parse(self, stream):
        raise NotImplementedError()
    def build(self, val, stream):
        raise NotImplementedError()

class Primitive(Construct):
    __slots__ = ["fmt"]
    def __init__(self, fmt):
        self.fmt = _Struct(fmt)
    def parse(self, stream):
        return self.fmt.unpack(stream.read(self.fmt.size))[0]
    def build(self, val, stream):
        return stream.write(self.fmt.pack(val))

sint8 = Primitive("b")
uint8 = Primitive("B")
sint32 = Primitive("l")
uint32 = Primitive("L")

class Bytes(Construct):
    __slots__ = ["count"]
    def __init__(self, count):
        self.count = count
    def parse(self, stream):
        return stream.read(self.count)
    def build(self, val, stream):
        assert len(val) == self.count
        return stream.write(val)

byte = Bytes(1)

class Constructive(Construct):
    def __init__(self, gen, container):
        self.gen = gen
        self.container = container
    def __repr__(self):
        return "<constructive %s>" % (self.gen.__name__,)
    def parse(self, stream):
        cont = self.container()
        val = None
        while True:
            try:
                name, cons = self.gen.send(val)
            except StopIteration:
                break
            if isinstance(cons, Construct):
                val = cons.parse(stream)
            else:
                val = cons
            if name is not None:
                cont[name] = val
        return cont
    def build(self, val, stream):
        val2 = None
        while True:
            try:
                name, cons = self.gen.send(val2)
            except StopIteration:
                break
            if name is None:
                val2 = None
            else:
                val2 = val[name]
            cons.build(val2, stream)

def constructive(container):
    def deco(func):
        def wrapper(*args, **kwargs):
            gen = func(*args, **kwargs)
            assert isinstance(gen, GeneratorType)
            return Constructive(gen, container)
        return wrapper
    return deco


@constructive(dict)
def point():
    yield "x", sint32
    yield "y", sint32


@constructive(dict)
def twopoints():
    yield "p1", point()
    yield "p2", point()


print twopoints().parse(BytesIO("1111222233334444"))

s = BytesIO()
twopoints().build(dict(p1=dict(x=0x1111,y=0x2222), p2=dict(x=0x3333,y=0x4444)), s)
print s.getvalue().encode("hex")


@constructive(dict)
def pascal_string():
    count = yield "count", uint8
    yield "data", Bytes(count)

print pascal_string().parse(BytesIO("\x05hello"))



@constructive(dict)
def c_string():
    i = 0
    while True:
        ch = yield i, byte
        if ch == "\x00":
            break
        i += 1

print c_string().parse(BytesIO("hello\x00"))

s = BytesIO()
c_string().build(dict(enumerate("hello\x00world")), s)
print repr(s.getvalue())







