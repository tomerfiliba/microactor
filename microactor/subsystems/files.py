from microactor.subsystems.base import Subsystem
from microactor.utils import Deferred
from microactor.transports.files import FileTransport


class FilesSubsystem(Subsystem):
    NAME = "files"
    
    def open(self, path, mode = "rt"):
        fileobj = open(path, mode)
        mode2 = ""
        if "r" in mode or "+" in mode:
            mode2 += "r"
        if "a" in mode or "+" in mode:
            mode2 += "w"
        return Deferred(FileTransport(self.reactor, fileobj, mode2))



