from ..base import BaseReactor
from microactor.utils import safe_import, MissingModule
from .subsystems import IOCP_SUBSYSTEMS
try:
    from . import lowlevel
except ImportError as ex:
    lowlevel = MissingModule(str(ex))
win32file = safe_import("win32file")


class IocpReactor(BaseReactor):
    SUBSYSTEMS = BaseReactor.SUBSYSTEMS + IOCP_SUBSYSTEMS
    
    def __init__(self):
        BaseReactor.__init__(self)
        self._port = lowlevel.IOCP()
        self._transports = set()
        self._overlap_callbacks = {}
    
    @classmethod
    def supported(cls):
        return bool(lowlevel)

    def register_transport(self, transport):
        if transport in self._transports:
            return
        self._port.register(transport)
        self._transports.add(transport)

    def _wakeup(self):
        self._port.post()

    def _get_overlapped(self, callback):
        overlapped = win32file.OVERLAPPED()
        self._overlap_callbacks[overlapped] = callback
        return overlapped
    
    def _discard_overlapped(self, overlapped):
        self._overlap_callbacks.pop(overlapped, None)

    def _handle_transports(self, timeout):
        for size, overlapped in self._port.get_events(timeout):
            if not overlapped:
                continue
            cb = self._overlap_callbacks.pop(overlapped)
            self.call(cb, size, overlapped)










