class TransportError(Exception):
    pass
class TransportClosed(TransportError):
    pass
class TransportDetached(TransportError):
    pass
class ReadRequiresMoreData(TransportError):
    pass
class OverlappingRequestError(TransportError):
    pass


class InvalidFile(object):
    __slots__ = ["_exc"]
    closed = True
    def __init__(self, exc):
        self._exc = exc
    def __nonzero__(self):
        return False
    __bool__ = __nonzero__
    def close(self):
        pass
    def __int__(self):
        raise self._exc
    def fileno(self):
        raise self._exc
    def __getattr__(self, name):
        raise self._exc

ClosedFile = InvalidFile(TransportClosed)
DetachedFile = InvalidFile(TransportDetached)

