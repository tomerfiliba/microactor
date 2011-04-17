from .deferred import Deferred, ReactorDeferred, reactive, rreturn


class MissingModule(object):
    def __init__(self, modname, exc):
        self.__name__ = modname
        self._exc = exc
    def __bool__(self):
        return False
    __nonzero__ = __bool__
    def __getattr__(self, name):
        raise ImportError(self._exc)

def safe_import(modname):
    try:
        mod = __import__(modname, None, None, "*")
    except ImportError as ex:
        return MissingModule(modname, str(ex))
    else:
        return mod


