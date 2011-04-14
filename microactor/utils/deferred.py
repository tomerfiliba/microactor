class DeferredAlreadySet(Exception):
    pass


#def format_stack():
#    frames = inspect.stack()[1:]
#    return traceback.format_list((f[1], f[2], f[3], f[4][f[5]]) 
#        for f in reversed(frames))


class Deferred(object):
    __slots__ = ["reactor", "value", "canceled", "_callbacks"]
    def __init__(self, reactor, value = NotImplemented, is_exc = False):
        self.reactor = reactor
        self.value = ()
        self.canceled = False
        self._callbacks = []
    def __repr__(self):
        if self.cancelled:
            val = "canceled"
        elif not self.value:
            val = "pending"
        elif self.value[0]:
            val = "exception = %r" % (self.value[1],)
        else:
            val = "value = %r" % (self.value[1],)
        return "<Deferred %d, %s>" % (self.id, val)
    def is_set(self):
        return bool(self.value)
    def register(self, func):
        if self.cancelled:
            return
        if self.value is NotImplemented:
            self._callbacks.append(func)
        else:
            func(self.is_exc, self.value)
    def _set(self, is_exc, value):
        if self.cancelled:
            return
        if self.value:
            raise DeferredAlreadySet()
        self.value = (is_exc, value)
        for cb in self._callbacks:
            self.reactor.call(cb, is_exc, value)
    def set(self, value = None):
        self._set(False, value)
    def throw(self, exc):
        #t, v, tb = sys.exc_info()
        #if v:
        #    tbtext = "".join(traceback.format_exception(*))
        #    tbtext += "\nfrom:\n" + "".join(format_stack())
        #    if not hasattr(exc, "_inner_tb"):
        #        exc._inner_tb = [tbtext]
        #    else:
        #        exc._inner_tb.append(tbtext)
        self._set(True, exc)
    def cancel(self):
        if self.canceled:
            return
        self.canceled = True



