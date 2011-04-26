class Subsystem(object):
    NAME = None
    
    def __init__(self, reactor):
        assert self.NAME, "must set subsystem's name"
        self.reactor = reactor
    
    def _init(self):
        pass
    def _unload(self):
        pass
    
    @classmethod
    def supported(cls):
        return True


