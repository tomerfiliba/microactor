import socket


class AutoResetEvent(object):
    __slots__ = ["_wsock", "_rsock", "_is_set"]
    def __init__(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("localhost", 0))
        listener.listen(1)
        self._wsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._wsock.connect(listener.getsockname())
        self._rsock = listener.accept()[0]
        listener.close()
        self._is_set = False
    
    def close(self):
        self._wsock.shutdown(socket.SHUT_RDWR)
        self._rsock.shutdown(socket.SHUT_RDWR)
        self._wsock.close()
        self._rsock.close()
    
    def fileno(self):
        return self._rsock.fileno()
    
    def set(self):
        if self._is_set:
            return
        self._wsock.send("x")
        self._is_set = True
    
    def reset(self):
        if not self._is_set:
            return
        self._rsock.recv(100)
        self._is_set = False
    
    def is_set(self):
        return self._is_set

