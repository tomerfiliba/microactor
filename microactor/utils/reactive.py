import sys
import itertools
import traceback
from types import GeneratorType
import inspect


def format_stack():
    frames = inspect.stack()[1:]
    return traceback.format_list((f[1], f[2], f[3], f[4][f[5]]) 
        for f in reversed(frames))


class DeferredAlreadySet(Exception):
    pass

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
        if with_traceback:
            tbtext = "".join(traceback.format_exception(*sys.exc_info()))
            tbtext += "\nfrom:\n" + "".join(format_stack())
            if not hasattr(exc, "_inner_tb"):
                exc._inner_tb = [tbtext]
            else:
                exc._inner_tb.append(tbtext)
        self.set(exc, True)
    def cancel(self, exc = None):
        if self.cancelled:
            return
        if exc is not None:
            self.throw(exc)
        self.cancelled = True


class ReactiveReturn(Exception):
    def __init__(self, value):
        self.value = value

class ReactiveError(Exception):
    pass

def rreturn(value = None):
    raise ReactiveReturn(value)

class TimedOut(Exception):
    pass

def timed(reactor, timeout, dfr):
    def cancel(job):
        if not dfr.is_set():
            dfr.register(lambda *args: dfr.cancel())
            reactor.call(dfr.throw, TimedOut())
    reactor.schedule(timeout, cancel)

def parallel(reactor, func, *args, **kwargs):
    return reactor.call(func, args, kwargs)

def reactive(func):
    def wrapper(*args, **kwargs):
        def continuation(is_exc, value):
            while True:
                try:
                    if is_exc:
                        dfr = gen.throw(value)
                    else:
                        dfr = gen.send(value)
                except (GeneratorExit, StopIteration):
                    retval.set()
                except ReactiveReturn as ex:
                    retval.set(ex.value)
                except Exception as ex:
                    retval.throw(ex)
                else:
                    if not isinstance(dfr, Deferred):
                        value = dfr
                        continue
                    else:
                        dfr.register(continuation)
                break
        
        retval = Deferred()
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
                continuation(False, None)
            else:
                retval.set(gen)
        
        def print_traceback(is_exc, value):
            if is_exc:
                for tb in getattr(value, "_inner_tb", ()):
                    print >>sys.stderr, tb + "\n"
        retval.register(print_traceback)
        return retval
    
    return wrapper



