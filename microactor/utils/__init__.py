from .deferred import Deferred
from .reactive import rreturn, reactive
from .transport_wrappers import BufferedTransport, BoundTransport


class MissingModule(object):
    __slots__ = ("__name__", "__file__")
    def __init__(self, name):
        self.__name__ = name
        self.__file__ = None
    def __repr__(self):
        return "MissingModule(%r)" % (self.__name__,)
    def __nonzero__(self):
        return False
    __bool__ = __nonzero__
    def __getattr__(self, name):
        raise ImportError("could not import %r" % (self.__name__,))
    for meth in ["__call__", "__len__", "__iter__", "__getitem__", "__setitem__", 
            "__delitem__", "__add__", "__sub__", "__mul__", "__div__", "__hash__",
            "__gt__", "__lt__", "__le__", "__ge__", "__eq__", "__ne__", "__cmp__"
            "next", "__next__", "__contains__", "__reduce__", "__reduce_ex__"]:
        exec("""def %s(self, *args, **kwargs):
            raise ImportError("could not import %%r" %% (self.__name__,))""" % (meth,)) 

def safe_import(modname, attrname = None):
    try:
        mod = __import__(modname, None, None, "*")
    except ImportError:
        if attrname:
            return MissingModule("%s from %s" % (attrname, modname))
        else:
            return MissingModule(modname)
    if attrname:
        return getattr(mod, attrname, MissingModule("%s from %s" % (attrname, modname)))
    else:
        return mod


