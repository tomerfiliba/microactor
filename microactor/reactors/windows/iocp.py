import time
import itertools
from ..base import BaseReactor
from .subsystems import SPECIFIC_SUBSYSTEMS
try:
    from ._iocp import IOCP
except ImportError:
    IOCP = None


class IocpReactor(BaseReactor):
    SUBSYSTEMS = BaseReactor.SUBSYSTEMS + SPECIFIC_SUBSYSTEMS
    MAX_POLLING_TIMEOUT = 0.2   # to handle Ctrl+C faster
    
    def __init__(self):
        BaseReactor.__init__(self)
        self._iocp = IOCP()
        self._transports = set()
    
    @classmethod
    def supported(cls):
        return bool(IOCP)
    
    def _shutdown(self):
        pass

    def register_transport(self, transport):
        self._iocp.register(transport.fileno())
        self._transports.add(transport)

    def wakeup(self):
        self._iocp.post()
    
    def _handle_transports(self, timeout):
        tmax = time.time() + timeout
        while True:
            res = self._iocp.wait(timeout)
            if not res:
                break
            size, _, overlapped = res
            self.call(overlapped.object, size, overlapped)
            if time.time() > tmax:
                break
            timeout = 0
    
    








