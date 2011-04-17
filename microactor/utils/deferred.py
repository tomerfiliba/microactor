import functools
from types import GeneratorType


class DeferredAlreadySet(Exception):
    pass


class Deferred(object):
    __slots__ = ["value", "_callbacks", "canceled"]
    def __init__(self, value = NotImplemented):
        if value is NotImplemented:
            self.value = None
        else:
            self.value = (False, value)
        self._callbacks = []
        self.canceled = False
    def register(self, func):
        if self.canceled:
            return
        elif self.is_set():
            func(*self.value)
        else:
            self._callbacks.append(func)
    def cancel(self):
        self.canceled = True
    def is_set(self):
        return bool(self.value)
    def _set(self, is_exc, val):
        if self.canceled:
            return
        if self.is_set():
            raise DeferredAlreadySet(self)
        self.value = (is_exc, val)
        for func in self._callbacks:
            func(is_exc, val)
        del self._callbacks
    def set(self, value = None):
        self._set(False, value)
    def throw(self, exc):
        self._set(True, exc)


class ReactorDeferred(Deferred):
    __slots__ = ["reactor"]
    def __init__(self, reactor, value = NotImplemented):
        Deferred.__init__(self, value)
        self.reactor = reactor
    def register(self, func):
        func2 = lambda is_exc, val: self.reactor.call(func, is_exc, val)
        Deferred.register(self, func2)


class ReactiveReturn(Exception):
    def __init__(self, value):
        self.value = value

def rreturn(value):
    raise ReactiveReturn(value)

def reactive(func):
    def wrapper(*args, **kwargs):
        def continuation(is_exc, val, gen = None, retval = None):
            while True:
                try:
                    if is_exc:
                        res = gen.throw(val)
                    else:
                        res = gen.send(val)
                except (GeneratorExit, StopIteration):
                    retval.set()
                except ReactiveReturn as ex:
                    retval.set(ex.value)
                except Exception as ex:
                    retval.throw(ex)
                else:
                    if isinstance(res, Deferred):
                        res.register(continuation)
                    else:
                        val = res
                        continue
                break
        
        retval = Deferred()
        def excepthook(is_exc, val):
            if is_exc:
                print "$$", repr(val)
        retval.register(excepthook)
        try:        
            gen = func(*args, **kwargs)
        except (GeneratorExit, StopIteration):
            retval.set()
        except ReactiveReturn as ex:
            retval.set(ex.value)
        except Exception as ex:
            retval.throw(ex)
        else:
            if isinstance(gen, GeneratorType):
                continuation.func_defaults = (gen, retval)
                continuation(False, None)
            elif isinstance(gen, Deferred):
                gen.register(retval._set)
            else:
                retval.set(gen)
        return retval
    
    functools.update_wrapper(wrapper, func)
    return wrapper







