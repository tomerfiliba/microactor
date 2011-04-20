import socket
from microactor.subsystems import Subsystem
from microactor.subsystems.net import NetSubsystem
from microactor.utils import ReactorDeferred, reactive, rreturn, safe_import
from .transports import (SocketStreamTransport, ListeningSocketTransport, 
    PipeTransport, FileTransport)
win32file = safe_import("win32file")
win32iocp = safe_import("microactor.arch.windows.iocp")


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

class LowlevelIOSubsystem(Subsystem):
    NAME = "_io"
    
    def wrap_pipe(self, fileobj, mode):
        return PipeTransport(self.reactor, fileobj, mode)
    
    def open(self, filename, mode):
        fobj, access = win32iocp.WinFile.open(filename, mode)
        return FileTransport(self.reactor, fobj, access)
    def pipe(self):
        rh, wh = win32iocp.create_overlapped_pipe()
        rtrns = PipeTransport(self.reactor, win32iocp.WinFile(rh), "r")
        wtrns = PipeTransport(self.reactor, win32iocp.WinFile(wh), "w")
        return rtrns, wtrns


IOCP_SUBSYSTEMS = [LowlevelIOSubsystem, IocpNetSubsystem]
