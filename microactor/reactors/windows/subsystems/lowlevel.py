from microactor.subsystems import Subsystem
from ..transports.files import FileTransport, PipeTransport


class LowLevelIOSubsystem(Subsystem):
    NAME = "_io"
    
    def wrap_pipe(self, fileobj, mode):
        return PipeTransport(self.reactor, fileobj, mode)
    def wrap_file(self, fileobj, mode):
        return FileTransport(self.reactor, fileobj, mode)
    
    def _open(self, filename):
        pass







