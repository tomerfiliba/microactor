from .deferred import Deferred
from .reactive import rreturn, reactive
from .transport_wrappers import BufferedTransport, BoundTransport


class MissingModule(object):
    def __init__(self, name):
        self.__name__ = name
        self.__file__ = None
    def __nonzero__(self):
        return False
    __bool__ = __nonzero__
    def __getattr__(self, name):
        raise ImportError("could not import %r" % (self.__name__,))

def safe_import(modname):
    try:
        mod = __import__(modname, None, None, "*")
    except ImportError:
        mod = MissingModule(modname)
    return mod


