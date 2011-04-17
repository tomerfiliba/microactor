import time
from ..base import BaseReactor
from microactor.utils import MissingModule
from .subsystems import SPECIFIC_SUBSYSTEMS
try:
    from . import lowlevel
except ImportError as ex:
    lowlevel = MissingModule(str(ex))


class IocpReactor(BaseReactor):
    SUBSYSTEMS = BaseReactor.SUBSYSTEMS + SPECIFIC_SUBSYSTEMS
    MAX_POLLING_TIMEOUT = 0.2   # to handle Ctrl+C faster
    
    def __init__(self):
        BaseReactor.__init__(self)
        self._iocp = lowlevel.IOCP()
        self._transports = set()
    
    @classmethod
    def supported(cls):
        return bool(lowlevel)
    
    def _shutdown(self):
        pass

    def register_transport(self, transport):
        if transport in self._transports:
            return
        self._iocp.register(transport)
        self._transports.add(transport)

    def wakeup(self):
        self._iocp.post()
    
    def _handle_transports(self, timeout):
        tmax = time.time() + timeout
        while True:
            res = self._iocp.wait(timeout)
            print "reactor got", res
            if not res:
                break
            size, _, overlapped = res
            self.call(overlapped.object, size, overlapped)
            if time.time() > tmax:
                break
            timeout = 0
    
    








