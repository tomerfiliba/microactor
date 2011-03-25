from types import GeneratorType


class DeferredAlreadySet(Exception):
    pass

class Deferred(object):
    def __init__(self, value = NotImplemented, is_exc = False):
        self.value = value
        self.is_exc = is_exc
        self._callbacks = []
    def is_set(self):
        return self.value is not NotImplemented
    def register(self, func):
        if self.value is NotImplemented:
            self._callbacks.append(func)
        else:
            func(self.is_exc, self.value)
    def set(self, value = None, is_exc = False):
        if self.is_set():
            raise DeferredAlreadySet()
        self.is_exc = is_exc
        self.value = value
        for func in self._callbacks:
            func(is_exc, value)
    def throw(self, exc):
        self.set(exc, True)


class ReactiveReturn(Exception):
    def __init__(self, value):
        self.value = value

class ReactiveError(Exception):
    pass

def rreturn(value = None):
    raise ReactiveReturn(value)

class Parallel(object):
    def __init__(self, func, args, kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
    def __call__(self):
        self.func(*self.args, **self.kwargs)

def parallel(func, *args, **kwargs):
    return Parallel(func, args, kwargs)

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
        return retval
    return wrapper













