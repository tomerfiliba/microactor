import sys
import os
from microactor.subsystems import Subsystem
from microactor.utils import Deferred, reactive, rreturn, BufferedTransport
from ..transports.files import FileTransport, PipeTransport


class FilesSubsystem(Subsystem):
    NAME = "files"
    
    def _init(self):
        self.stdin = self.wrap_pipe(sys.stdin, "r")
        self.stdout = self.wrap_pipe(sys.stdout, "w")
        self.stderr = self.wrap_pipe(sys.stderr, "w")
    
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

    @reactive
    def open_buffered(self, path, mode = "rt"):
        trns = yield self.open()
        rreturn(BufferedTransport(self.reactor, trns))
    
    def open_pipe(self):
        """returns a (read-pipe, write-pipe) pair of transports"""
        def opener():
            try:
                rfd, wfd = os.pipe()
            except Exception as ex:
                self.reactor.call(dfr.throw, ex)
            else:
                rtrns = self.wrap_pipe(os.fdopen(rfd, "r"), "r")
                wtrns = self.wrap_pipe(os.fdopen(wfd, "w"), "w")
                self.reactor.call(dfr.set, (rtrns, wtrns))
        
        dfr = Deferred()
        self.reactor.call(opener)
        return dfr
    
    def wrap_pipe(self, fileobj, mode):
        return PipeTransport(self.reactor, fileobj, mode)







