import select
from .base import BaseReactor


class KqueueReactor(BaseReactor):
    def __init__(self):
        BaseReactor.__init__(self)
        self._poller = select.kqueue()
    
    @classmethod
    def supported(cls):
        return False
        #return hasattr(select, "kqueue")
    
    def _handle_transports(self, timeout):
        pass





