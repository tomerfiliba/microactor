from ..base import BaseReactor, ReactorError
from microactor.utils import safe_import
from .subsystems import IOCP_SUBSYSTEMS
win32iocp = safe_import("microactor.arch.windows.iocp")
win32file = safe_import("win32file")


class IocpReactor(BaseReactor):
    SUBSYSTEMS = BaseReactor.SUBSYSTEMS + IOCP_SUBSYSTEMS
    
    def __init__(self):
        BaseReactor.__init__(self)
        self._port = win32iocp.IOCP()
        self._transports = {}
        self._overlap_callbacks = {}
        self._install_builtin_subsystems()
    
    @classmethod
    def supported(cls):
        return bool(win32iocp)

    def register_transport(self, transport):
        fd = transport.fileno()
        if fd in self._transports:
            orig = self._transports[fd]
            if transport is orig:
                return
            else:
                try:
                    orig.fileno()
                except EnvironmentError:
                    alive = False
                else:
                    alive = True
                if alive:
                    raise ReactorError("")
        self._port.register(transport.fileno())
        self._transports[fd] = transport

    def _detach(self, transport):
        pass

    def _wakeup(self):
        self._port.post()

    def _get_overlapped(self, callback):
        overlapped = win32file.OVERLAPPED()
        self._overlap_callbacks[overlapped] = callback
        return overlapped
    
    def _discard_overlapped(self, overlapped):
        self._overlap_callbacks.pop(overlapped, None)

    def _handle_transports(self, timeout):
        for size, overlapped, exc in self._port.get_events(timeout):
            cb = self._overlap_callbacks.pop(overlapped)
            self.call(cb, size, exc)










