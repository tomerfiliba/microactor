import sys
import itertools
#import traceback
#import inspect


class DeferredAlreadySet(Exception):
    pass


#def format_stack():
#    frames = inspect.stack()[1:]
#    return traceback.format_list((f[1], f[2], f[3], f[4][f[5]]) 
#        for f in reversed(frames))


class Deferred(object):
    ID_GENERATOR = itertools.count()
    
    def __init__(self, value = NotImplemented, is_exc = False):
        self.id = self.ID_GENERATOR.next()
        self.value = value
        self.is_exc = is_exc
        self.cancelled = False
        self._callbacks = []
    def __repr__(self):
        val = "value = %r" % (self.value,) if self.value is not NotImplemented else "pending"
        return "<Deferred %d, %s>" % (self.id, val)
    def is_set(self):
        return self.value is not NotImplemented
    def register(self, func):
        if self.cancelled:
            return
        if self.value is NotImplemented:
            self._callbacks.append(func)
        else:
            func(self.is_exc, self.value)
    def set(self, value = None, is_exc = False):
        if self.cancelled:
            return
        if self.is_set():
            raise DeferredAlreadySet()
        self.is_exc = is_exc
        self.value = value
        for func in self._callbacks:
            func(is_exc, value)
    def throw(self, exc, with_traceback = True):
        #if with_traceback:
        #    tbtext = "".join(traceback.format_exception(*sys.exc_info()))
        #    tbtext += "\nfrom:\n" + "".join(format_stack())
        #    if not hasattr(exc, "_inner_tb"):
        #        exc._inner_tb = [tbtext]
        #    else:
        #        exc._inner_tb.append(tbtext)
        self.set(exc, True)
    def cancel(self, exc = None):
        if self.cancelled:
            return
        if exc is not None:
            self.throw(exc)
        self.cancelled = True



