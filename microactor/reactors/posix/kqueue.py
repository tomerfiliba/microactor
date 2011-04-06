import select
from .base import BasePosixReactor


class KqueueReactor(BasePosixReactor):
    def __init__(self):
        BasePosixReactor.__init__(self)
        self._poller = select.kqueue()
    
    @classmethod
    def supported(cls):
        return False
        #return hasattr(select, "kqueue")
    
    def _handle_transports(self, timeout):
        pass





