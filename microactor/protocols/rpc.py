from microactor.utils import reactive
from microactor.lib.colls import ReactiveQueue
from struct import Struct
from .base import Module


UBInt32 = Struct("!L")

class RPCError(Exception):
    pass


class RPCService(object):
    def _resolve(self, funcname):
        if not isinstance(funcname, str) or funcname.startswith("_"):
            raise RPCError("invalid function: %r" % (funcname,))
        func = getattr(self.service, funcname, None)
        if not func:
            raise RPCError("no such function: %r" % (funcname,))
        return func
        

class RPCModule(Module):
    def __init__(self, reactor, service, input, output):
        self.reactor = reactor
        self.input = input
        self.output = output
        self.incoming = ReactiveQueue()
        self.outgoing = ReactiveQueue()
        self.active = True
        self.service = service
    
    @classmethod
    def over_stdio(cls, reactor, service):
        return cls(reactor, service, reactor.files.stdin, reactor.files.stdout)

    @reactive
    def fetch_incoming(self):
        try:
            while self.active:
                raw_length = yield self.input.read_exactly(4)
                length = UBInt32.unpack(raw_length)
                packet = yield self.input.read_exactly(length)
                yield self.incoming.push(packet)
        except EOFError:
            self.active = False

    @reactive
    def send_outgoing(self):
        try:
            while self.active:
                packet = yield self.outgoing.pop()
                length = UBInt32.pack(len(packet))
                self.output.write(length)
                self.output.write(packet)
                self.output.write.flush()
        except EOFError:
            self.active = False
        
    @reactive
    def main(self):
        self.reactor.call(self.fetch_incoming)
        self.reactor.call(self.send_outgoing)
        while self.active:
            packet = yield self.incoming.pop()
            msg = self._load(packet)
            self.reactor.call(self._dispatch, msg)

    def _load(self, data):
        pass
    
    def _dump(self, obj):
        pass
    
    @reactive
    def _dispatch(self, msg):
        try:
            func = self.service._resolve(msg.funcname)
            res = yield func(*msg.args, **msg.kwargs)
        except Exception as ex:
            packet = self._dump((msg.seq, False, ex))
        else:
            packet = self._dump((msg.seq, True, res))
        self.outgoing.push(packet)









