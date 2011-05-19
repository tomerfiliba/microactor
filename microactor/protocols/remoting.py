import pickle
import itertools
import sys
import traceback
import weakref
from microactor.utils import reactive
from microactor.utils.deferred import ReactorDeferred, rreturn
from microactor.reactors.transports import TransportClosed
from microactor.subsystems.net import BaseSocketHandler
from microactor.utils.transports import PacketTransport


class BaseService(object):
    @reactive
    def dispatch(self, funcname, args, kwargs):
        func = getattr(self, "exposed_%s" % (funcname,))
        res = yield func(*args, **kwargs)
        rreturn(res)


class RemotingServer(BaseSocketHandler):
    def __init__(self, reactor, server, conn, service):
        BaseSocketHandler.__init__(self, reactor, server, PacketTransport(conn))
        self.service = service
    
    @classmethod
    def of(cls, service):
        return lambda reactor, server, conn: cls(reactor, server, conn, server)
    
    @reactive
    def start(self):
        while True:
            try:
                data = yield self.conn.recv()
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
        yield self.conn.send(data)


class RemotingNamespace(object):
    __slots__ = ["_client"]
    def __init__(self, client):
        self._client = client
    def __getattr__(self, name):
        return lambda *args, **kwargs: self._client.call(name, *args, **kwargs)

class RemotingClient(object):
    def __init__(self, reactor, transport):
        self.reactor = reactor
        self.transport = PacketTransport(transport)
        self.seq = itertools.count()
        self.replies = {}
        self.reactor.call(self._process_incoming)
        self.api = RemotingNamespace(weakref.proxy(self))

    @classmethod
    @reactive
    def connect(cls, reactor, host, port):
        sock = yield reactor.net.connect_tcp(host, port)
        rreturn(cls(reactor, sock))

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
                yield self.close()
                break
            
            dfr = self.replies.pop(seq)
            if isexc:
                dfr.throw(obj)
            else:
                dfr.set(obj)
    
    @reactive
    def call(self, funcname, *args, **kwargs):
        seq = self.seq.next()
        data = self.pack((seq, funcname, args, kwargs))
        yield self.transport.send(data)
        dfr = ReactorDeferred(self.reactor)
        self.replies[seq] = dfr
        obj = yield dfr
        rreturn(obj)

    def unpack(self, data):
        return pickle.loads(data)
    def pack(self, obj):
        return pickle.dumps(obj)

















