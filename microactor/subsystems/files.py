import sys
import os
from microactor.subsystems import Subsystem
from microactor.utils import Deferred, BufferedTransport
from ..transports.files import FileTransport, PipeTransport


class FilesSubsystem(Subsystem):
    NAME = "files"
    
    def _init(self):
        self._stdin = None
        self._stdout = None
        self._stderr = None
    
    @property
    def stdin(self):
        if not self._stdin:
            self._stdin = self.reactor._io.wrap_pipe(sys.stdin, "r")
        return self._stdin
    
    @property
    def stdout(self):
        if not self._stdout:
            self._stdout = self.reactor._io.wrap_pipe(sys.stdout, "w")
        return self._stdout

    @property
    def stderr(self):
        if not self._stderr:
            self._stderr = self.reactor._io.wrap_pipe(sys.stderr, "w")
        return self._stderr
    
    def open(self, path, mode = "rt", buffering = False):
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
            trns = self.reactor._io.wrap_file(fileobj, mode2)
            if buffering:
                trns = BufferedTransport(trns)
            self.reactor.call(dfr.set, trns)
        
        dfr = Deferred()
        self.reactor.call(opener)
        return dfr

    def open_pipes(self, buffered = False):
        """returns a (read-pipe, write-pipe) pair of transports"""
        def opener():
            try:
                rfd, wfd = os.pipe()
            except Exception as ex:
                self.reactor.call(dfr.throw, ex)
            else:
                rtrns = self.reactor._io.wrap_pipe(os.fdopen(rfd, "r"), "r")
                wtrns = self.reactor._io.wrap_pipe(os.fdopen(wfd, "w"), "w")
                self.reactor.call(dfr.set, (rtrns, wtrns))
        
        dfr = Deferred()
        self.reactor.call(opener)
        return dfr






