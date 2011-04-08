import sys
from types import GeneratorType
from .deferred import Deferred
 

class ReactiveReturn(Exception):
    def __init__(self, value):
        self.value = value

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
            elif isinstance(gen, Deferred):
                gen.register(lambda is_exc, value: retval.set(value, is_exc))
            else:
                retval.set(gen)
        
        def print_traceback(is_exc, value):
            if is_exc:
                for tb in getattr(value, "_inner_tb", ()):
                    print >>sys.stderr, tb + "\n"
        retval.register(print_traceback)
        return retval
    
    return wrapper



