import sys
import inspect
import traceback


class DeferredAlreadySet(Exception):
    pass


def format_stack(ignore = 1):
    frames = inspect.stack()[ignore:]
    return traceback.format_list((f[1], f[2], f[3], f[4][f[5]]) 
        for f in reversed(frames))

class Deferred(object):
    __slots__ = ["reactor", "value", "canceled", "_callbacks", "traceback"]
    def __init__(self, reactor, value = NotImplemented, is_exc = False):
        self.reactor = reactor
        self.value = ()
        self.canceled = False
        self._callbacks = []
        self.traceback = [format_stack(2)]
    def __repr__(self):
        if self.canceled:
            val = "canceled"
        elif not self.value:
            val = "pending"
        elif self.value[0]:
            val = "exception = %r" % (self.value[1],)
        else:
            val = "value = %r" % (self.value[1],)
        return "<Deferred at 0x%08X, %s>" % (id(self), val)
    def is_set(self):
        return bool(self.value)
    def register(self, func):
        if self.canceled:
            return
        if not self.value:
            self._callbacks.append(func)
        else:
            self.reactor.call(func, *self.value)
    def _set(self, is_exc, value):
        if self.canceled:
            return
        if self.value:
            raise DeferredAlreadySet()
        self.value = (is_exc, value)
        for cb in self._callbacks:
            self.reactor.call(cb, is_exc, value)
        if is_exc and not self._callbacks:
            for tb in self.traceback:
                print >>sys.stderr, tb
                print >>sys.stderr, "-----------------------------------------"
        del self._callbacks[:]
    def set(self, value = None):
        self._set(False, value)
    def throw(self, exc):
        t, v, tb = sys.exc_info()
        self.traceback.append("".join(format_stack(2)))
        if v:
            self.traceback.append("".join(traceback.format_exception(t, v, tb)))
        self._set(True, exc)
    def cancel(self):
        if self.canceled:
            return
        self.canceled = True



