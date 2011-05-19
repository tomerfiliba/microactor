import pickle
import itertools
import sys
import traceback
import weakref
from microactor.utils import reactive
from microactor.utils.deferred import ReactorDeferred, rreturn
from microactor.reactors.transports import TransportClosed
from microactor.utils.transports import PacketTransport
from microactor.subsystems.net import BaseHandler


class BaseService(object):
    __slots__ = ["reactor"]
    def __init__(self, reactor):
        self.reactor = reactor
    @reactive
    def dispatch(self, funcname, args, kwargs):
        func = getattr(self, "exposed_%s" % (funcname,))
        res = yield func(*args, **kwargs)
        rreturn(res)


class RemotingHandler(BaseHandler):
    def __init__(self, service_factory, transport, owner = None):
        BaseHandler.__init__(self, PacketTransport(transport), owner)
        self.service = service_factory(self.reactor)
    
    @classmethod
    def of(cls, service_factory):
        return lambda transport, owner = None: cls(service_factory, transport, owner)
    
    @reactive
    def start(self):
        while True:
            try:
                data = yield self.transport.recv()
            except (EOFError, TransportClosed):
                break
            self.reactor.call(self.dispatch, data)
        yield self.close()

    def unpack(self, data):
        return pickle.loads(data)
    def pack(self, obj):
        return pickle.dumps(obj)

    @reactive
    def dispatch(self, data):
        try:
            seq, funcname, args, kwargs = self.unpack(data)
            res = yield self.service.dispatch(funcname, args, kwargs)
        except Exception as ex:
            ex.traceback = "".join(traceback.format_exception(*sys.exc_info()))
            reply = (seq, True, ex)
        else:
            reply = (seq, False, res)
        data = self.pack(reply)
        yield self.transport.send(data)


class RemotingNamespace(object):
    __slots__ = ["_client"]
    def __init__(self, client):
        self._client = client
    def __getattr__(self, name):
        return lambda *args, **kwargs: self._client.call(name, *args, **kwargs)

class RemotingClient(object):
    def __init__(self, transport):
        self.reactor = transport.reactor
        self.transport = PacketTransport(transport)
        self.seq = itertools.count()
        self.replies = {}
        self.reactor.call(self._process_incoming)
        self.api = RemotingNamespace(weakref.proxy(self))

    @classmethod
    @reactive
    def connect(cls, reactor, host, port):
        trns = yield reactor.net.connect_tcp(host, port)
        rreturn(cls(trns))

    @reactive
    def close(self):
        yield self.transport.close()
    
    @reactive
    def _process_incoming(self):
        while True:
            try:
                data = yield self.transport.recv()
            except (EOFError, TransportClosed):
                break
            try:
                seq, isexc, obj = self.unpack(data)
            except (TypeError, ValueError) as ex:
                print "PROTOCOL ERROR", ex
                yield self.close()
                break
            if seq not in self.replies:
                print "INVALID SEQ", seq
                yield self.close()
                break
            
            dfr = self.replies.pop(seq)
            if isexc:
                dfr.throw(obj)
            else:
                dfr.set(obj)
    
    @reactive
    def call(self, funcname, *args, **kwargs):
        dfr = yield self._call(funcname, args, kwargs)
        obj = yield dfr
        rreturn(obj)

    @reactive
    def _call(self, funcname, args, kwargs):
        seq = self.seq.next()
        data = self.pack((seq, funcname, args, kwargs))
        yield self.transport.send(data)
        dfr = ReactorDeferred(self.reactor)
        self.replies[seq] = dfr
        rreturn(dfr)

    def unpack(self, data):
        return pickle.loads(data)
    def pack(self, obj):
        return pickle.dumps(obj)








