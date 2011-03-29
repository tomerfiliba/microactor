from .reactive import Deferred
from microactor.lib import Queue


class Mutex(object):
    def __init__(self):
        self.owned = False
        self.queue = Queue()
    
    def acquire(self):
        dfr = Deferred()
        if not self.owned:
            self.owned = True
            dfr.set()
        else:
            self.queue.push(dfr)
        return dfr
    
    def release(self):
        if not self.queue:
            self.owned = False
        else:
            dfr = self.queue.pop()
            dfr.set()




