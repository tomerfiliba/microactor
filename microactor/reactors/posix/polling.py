import select
from .base import BasePosixReactor


class PollReactor(BasePosixReactor):
    def __init__(self):
        BasePosixReactor.__init__(self)
        self._poller = select.poll()
    
    @classmethod
    def supported(cls):
        return False
        #return hasattr(select, "poll")
    
    def _handle_transports(self, timeout):
        pass





