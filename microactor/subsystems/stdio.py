import sys
from microactor.subsystems.base import Subsystem
from microactor.transports import PipeTransport


class StdioSubsystem(Subsystem):
    NAME = "stdio"
    
    def _init(self):
        self.stdin = PipeTransport(self.reactor, sys.stdin, "r")
        self.stdout = PipeTransport(self.reactor, sys.stdout, "w")
        self.stderr = PipeTransport(self.reactor, sys.stderr, "w")
    


