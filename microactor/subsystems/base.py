class Subsystem(object):
    DEPENDENCIES = []
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


class UnsupportedSubsystemException(Exception):
    pass

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


_initialzation_stack = []
def _init_with_deps(subsys):
    if subsys._initialized:
        return
    if subsys in _initialzation_stack:
        _initialzation_stack.append(subsys)
        cycle = "->".join(s.NAME for s in _initialzation_stack)
        raise ValueError("Cyclic dependency detected: %s" % (cycle,))
    _initialzation_stack.append(subsys)
    for name in subsys.DEPENDENCIES:
        try:
            dep = getattr(subsys.reactor, name)
        except AttributeError:
            raise AttributeError("nonexistent subsystem: %r" % (name,))
        if isinstance(dep, UnsupportedSubsystem):
            raise UnsupportedSubsystemException(name)
        _init_with_deps(dep)
    subsys._init()
    subsys._initialized = True
    _initialzation_stack.pop(-1)

def init_subsystems(reactor, subsystems):
    instances = []
    for factory in subsystems:
        assert not hasattr(reactor, factory.NAME), "subsystem %s overrides existing attribute" % (factory.NAME,)
        if factory.supported():
            subsys = factory(reactor)
        else:
            subsys = UnsupportedSubsystem(reactor, factory.NAME)
        setattr(reactor, factory.NAME, subsys)
        instances.append(subsys)
    for subsys in instances:
        _init_with_deps(subsys)

