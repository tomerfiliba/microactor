from microactor.utils import Deferred
from microactor.reactors.posix.subsystems.files import FilesSubsystem as PosixFilesSubsystem
from ..transports.files import FileTransport, PipeTransport


class FilesSubsystem(PosixFilesSubsystem):

    def open(self, path, mode = "rt"):
        def opener():
            try:
                fileobj = open(path, mode)
            except Exception as ex:
                self.reactor.call(dfr.throw, ex)
                return
            mode2 = ""
            if "r" in mode or "+" in mode:
                mode2 += "r"
            if "a" in mode or "+" in mode:
                mode2 += "w"
            trns = FileTransport(self.reactor, fileobj, mode2)
            self.reactor.call(dfr.set, trns)
        
        dfr = Deferred()
        self.reactor.call(opener)
        return dfr
    
    def wrap_pipe(self, fileobj, mode):
        return PipeTransport(self.reactor, fileobj, mode)







