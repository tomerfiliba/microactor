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

def rreturn(value = None):
    raise ReactiveReturn(value)

def reactive(func):
    def wrapper(*args, **kwargs):
        def continuation(is_exc, value):
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
                dfr.register(continuation)
        
        retval = Deferred()
        try:
            gen = func(*args, **kwargs)
        except (GeneratorExit, StopIteration):
            retval.set()
        except ReactiveReturn as ex:
            retval.set(ex)
        except Exception as ex:
            retval.throw(ex)
        else:
            if isinstance(gen, GeneratorType):
                continuation(False, None)
            else:
                retval.set(gen)
        return retval
    return wrapper


