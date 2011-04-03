import select
from .base import BaseReactor


class PollReactor(BaseReactor):
    def __init__(self):
        BaseReactor.__init__(self)
        self._poller = select.poll()
    
    @classmethod
    def supported(cls):
        return False
        #return hasattr(select, "poll")
    
    def _handle_transports(self, timeout):
        pass





