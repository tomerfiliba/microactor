from .base import Subsystem


class SshContext(object):
    __slots__ = []


class SshTunnel(object):
    pass


class SshSubsystem(Subsystem):
    NAME = "sshtool"
    
    def __call__(self, *args, **kwargs):
        return SshContext(self.reactor, *args, **kwargs)

