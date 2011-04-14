from types import GeneratorType
from .deferred import Deferred
import microactor.reactors


class ReactiveReturn(Exception):
    def __init__(self, value):
        self.value = value

def rreturn(value = None):
    raise ReactiveReturn(value)

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
        
        retval = Deferred(microactor.reactors.get_reactor())
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
        return retval
    
    return wrapper



