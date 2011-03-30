import sys
import os
from microactor.subsystems.base import Subsystem
from microactor.utils import Deferred
from microactor.transports.files import FileTransport, PipeTransport
try:
    import fcntl
except ImportError:
    fcntl = None


class FilesSubsystem(Subsystem):
    NAME = "files"
    
    def _init(self):
        self._unblock(sys.stdin)
        self._unblock(sys.stdout)
        self._unblock(sys.stderr)
        self.stdin = PipeTransport(self.reactor, sys.stdin, "r")
        self.stdout = PipeTransport(self.reactor, sys.stdout, "w")
        self.stderr = PipeTransport(self.reactor, sys.stderr, "w")
    
    @classmethod
    def _unblock(cls, fd):
        if not fcntl:
            # windows... nothing we can do
            return
        flags = fcntl.fcntl(fd, fcntl.F_GETFL, 0)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    
    def open(self, path, mode = "rt"):
        def opener():
            try:
                fileobj = open(path, mode)
            except Exception as ex:
                dfr.throw(ex)
                return
            self._unblock(fileobj)
            mode2 = ""
            if "r" in mode or "+" in mode:
                mode2 += "r"
            if "a" in mode or "+" in mode:
                mode2 += "w"
            trns = FileTransport(self.reactor, fileobj, mode2)
            dfr.set(trns)
        
        dfr = Deferred()
        return dfr



