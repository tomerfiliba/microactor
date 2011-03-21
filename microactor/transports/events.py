import socket
from .base import BaseTransport


class Event(BaseTransport):
    def __init__(self, reactor, auto_reset = True):
        BaseTransport.__init__(self, reactor)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        self._wsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._wsock.connect(listener.getsockname())
        self._rsock, _ = listener.accept()
        listener.close()
        self._is_set = False
        self.auto_reset = auto_reset
    
    def close(self):
        BaseTransport.close(self)
        self._wsock.close()
        self._rsock.close()
    def fileno(self):
        return self._rsock.fileno()
    
    def set(self):
        if self._is_set:
            return
        self._is_set = True
        self._wsock.send("x")
    
    def reset(self):
        if not self._is_set:
            return
        self._rsock.recv(100)
        self._is_set = False

    def is_set(self):
        return self._is_set
    
    def on_read(self, hint):
        if self.auto_reset:
            self.reset()


















