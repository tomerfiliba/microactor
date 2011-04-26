import socket
from microactor.subsystems import Subsystem
from microactor.subsystems.net import NetSubsystem
from microactor.utils import ReactorDeferred, reactive, rreturn, safe_import
from .transports import (SocketStreamTransport, ListeningSocketTransport, 
    PipeTransport, FileTransport, ConsoleInputTransport)
import threading
import sys
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
        if winconsole.Console.is_attached():
            self.console = winconsole.Console()
            self._console_events = []
            self._console_buffer = ""
            self._console_input_dfr = None
            self._console_thd = threading.Thread(target = self._console_input_thread)
            self._console_thd.start()
        else:
            # XXX:
            # need to check if stdin has FLAG_FILE_FLAG_OVERLAPPED. if so, 
            # PipeStream will handle it fine. otherwise, let's start a thread
            # that just blocks on sys.stdin.read(1000) on that handle, and
            # enqueue the incoming data
            self.console = None
        self._stdin = None
        self._stdout = None
        self._stderr = None
    
    def _unload(self):
        if self.console:
            self.console.close()
            self.console = None
    
    @property
    def stdin(self):
        if not self._stdin:
            if self.console:
                self._stdin = ConsoleInputTransport(self)
            else:
                self._stdin = PipeTransport(self, sys.stdin, "r")
        return self._stdin
    
    @property
    def stdout(self):
        if not self._stdout:
            self._stdout = PipeTransport(self, sys.stdout, "w")
        return self._stdout
    
    @property
    def stderr(self):
        if not self._stderr:
            self._stderr = PipeTransport(self, sys.stderr, "w")
        return self._stderr
    
    def _fetch_console_input(self):
        #self._console_events.extend(self.console.get_events())
        self._console_buffer += self.console.read(1000)
        if self._console_input_dfr and not self._console_input_dfr.is_set():
            self._console_input_dfr.set(self._console_buffer)
            self._console_buffer = ""
            self._console_input_dfr = None
    
    def _request_console_read(self):
        if not self._console_input_dfr or self._console_input_dfr.is_set():
            self._console_input_dfr = ReactorDeferred(self.reactor)
        return self._console_input_dfr
    
    def _console_input_thread(self):
        while self.reactor._active:
            if self.console.wait_input(0.2):
                self.reactor.call(self._fetch_console_input)
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
