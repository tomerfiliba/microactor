import os
import socket
from microactor.subsystems import Subsystem
from microactor.subsystems.net import NetSubsystem
from microactor.utils import ReactorDeferred, reactive, rreturn, safe_import
from .transports import (SocketStreamTransport, ListeningSocketTransport, 
    PipeTransport, FileTransport, ConsoleInputTransport, BlockingStreamTransport)
import threading
import sys
msvcrt = safe_import("msvcrt") 
win32file = safe_import("win32file")
win32iocp = safe_import("microactor.arch.windows.iocp")
winconsole = safe_import("microactor.arch.windows.console") 


class IocpNetSubsystem(NetSubsystem):   
    @reactive
    def connect_tcp(self, host, port, timeout = None):
        def connect_finished(size, overlapped):
            trns_dfr.set(trns)

        yield self.reactor.started
        hostaddr = yield self.resolve(host)
        trns_dfr = ReactorDeferred(self.reactor)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.bind(('0.0.0.0', 0)) # ConnectEx requires the socket to be bound
        # this is required here to register the new socket with its IOCP
        trns = SocketStreamTransport(self.reactor, sock)
        overlapped = self.reactor._get_overlapped(connect_finished)
        try:
            win32file.ConnectEx(sock.fileno(), (hostaddr, port), overlapped)
        except Exception:
            self.reactor._discard_overlapped(overlapped)
            raise
        yield trns_dfr
        rreturn(trns)
    
    @reactive
    def listen_tcp(self, port, host = "0.0.0.0", backlog = 40):
        yield self.reactor.started
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.bind((host, port))
        sock.listen(backlog)
        rreturn(ListeningSocketTransport(self.reactor, sock))

class IOSubsystem(Subsystem):
    NAME = "io"
    
    def _init(self):
#        self._console_thd = None
#        if winconsole.Console.is_attached():
#            print "console attached"
#            self.console = winconsole.Console()
#            self._console_buffer = ""
#            self._console_input_dfr = None
#            self._console_thd = threading.Thread(target = self._console_input_thread)
#            self._console_thd.daemon = True
#            self._console_thd_started = False
#        else:
#            self.console = None
#            # check if stdin has FLAG_FILE_FLAG_OVERLAPPED by trying to register 
#            # it with the IOCP
#            handle = msvcrt.get_osfhandle(sys.stdin.fileno())
#            try:
#                self.reactor._port.register(handle)
#            except win32file.error:
#                print "no OVERLAPPED"
#                self._console_buffer = ""
#                self._console_input_dfr = None
#                self._console_thd = threading.Thread(target = self._console_input_thread)
#                self._console_thd.daemon = True
#                self._console_thd_started = False
#            else:
#                print "OVERLAPPED enabled"
#                # successfully registered with IOCP -- PipeTransport will work 
#                # just fine
#                pass
        self._stdin = None
        self._stdout = None
        self._stderr = None
    
    #def _unload(self):
    #    if self.console:
    #        self.console.close()
    #        self.console = None
    
    @property
    def stdin(self):
        if not self._stdin:
            #if getattr(self, "_console_thd", False):
            #    self._stdin = ConsoleInputTransport(self.reactor)
            #else:
            self._stdin = PipeTransport(self.reactor, sys.stdin, "r")
        return self._stdin
    
    @property
    def stdout(self):
        if not self._stdout:
            #if getattr(self, "_console_thd", False):
            #    self._stdout = BlockingStreamTransport(self, sys.stdout)
            #else:
            self._stdout = PipeTransport(self.reactor, sys.stdout, "w")
        return self._stdout
    
    @property
    def stderr(self):
        if not self._stderr:
            #if getattr(self, "_console_thd", False):
            #    self._stderr = BlockingStreamTransport(self, sys.stdout)
            #else:
            self._stderr = PipeTransport(self.reactor, sys.stderr, "w")
        return self._stderr
    
    def _assure_started(self):
        if getattr(self, "_console_thd", False) and not self._console_thd_started:
            self._console_thd.start()
            self._console_thd_started = True
    
    def _request_console_read(self):
        self._assure_started()
        if not self._console_input_dfr or self._console_input_dfr.is_set():
            self._console_input_dfr = ReactorDeferred(self.reactor)
        return self._console_input_dfr
    
    def _console_input_thread(self):
        while self.reactor._active:
            data = os.read(sys.stdin.fileno(), 1000)
            self._console_buffer += data
            
            if self._console_input_dfr and not self._console_input_dfr.is_set():
                self._console_input_dfr.set(self._console_buffer)
                self._console_buffer = ""
                self._console_input_dfr = None
                self.reactor._wakeup()
    
    def _wrap_pipe(self, fileobj, mode):
        return PipeTransport(self.reactor, fileobj, mode)
    
    @reactive
    def open(self, filename, mode):
        yield self.reactor.started
        fobj, access = win32iocp.WinFile.open(filename, mode)
        rreturn(FileTransport(self.reactor, fobj, access))
    
    @reactive
    def pipe(self):
        yield self.reactor.started
        rh, wh = win32iocp.create_overlapped_pipe()
        rtrns = PipeTransport(self.reactor, win32iocp.WinFile(rh), "r")
        wtrns = PipeTransport(self.reactor, win32iocp.WinFile(wh), "w")
        rreturn((rtrns, wtrns))


IOCP_SUBSYSTEMS = [IOSubsystem, IocpNetSubsystem]
