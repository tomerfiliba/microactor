class UnsupportedSubsystemException(Exception):
    pass


class Subsystem(object):
    NAME = None
    
    def __init__(self, reactor):
        assert self.NAME, "must set a name"
        self.reactor = reactor
        self._initialized = False
    def _init(self):
        pass
    
    @classmethod
    def supported(cls):
        return True

class UnsupportedSubsystem(Subsystem):
    NAME = "Unsupported"
    
    def __init__(self, reactor, name):
        self.reactor = reactor
        self.name = name
        self._initialized = True
    def __getattr__(self, name):
        raise UnsupportedSubsystemException(self.name)
    @classmethod
    def supported(cls):
        return False



