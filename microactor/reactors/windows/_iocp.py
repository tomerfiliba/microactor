import ctypes
import socket # to initialize winsock
import win32file
import win32con

if not hasattr(win32file, "CreateIoCompletionPort"):
    raise ImportError("win32file is missing CreateIoCompletionPort")


class IOCP(object):
    def __init__(self):
        self._port = win32file.CreateIoCompletionPort(win32file.INVALID_HANDLE_VALUE, None, 0, 0)
        self._key = itertools.count()
        self._post_key = self._key.next()
    def __repr__(self):
        return "IOCP(%r)" % (self._port,)
    def register(self, handle):
        """registers the given handle with the IOCP. the handle cannot be 
        unregistered"""
        if hasattr(handle, "fileno"):
            handle = handle.fileno()
        key = self._key.next()
        win32file.CreateIoCompletionPort(handle, self._port, key, 0)
        return key
    def post(self, key = None, size = 0, overlapped = None):
        """will cause wait() to return with the given information"""
        if key is None:
            key = self._post_key
        win32file.PostQueuedCompletionStatus(self._port, size, key, overlapped)
    def wait(self, timeout):
        """returns (size, key, overlapped) on success, None on timeout"""
        rc, size, key, overlapped = win32file.GetQueuedCompletionStatus(
            self._port, int(timeout * 1000))
        if rc == win32con.WAIT_TIMEOUT:
            return None
        else:
            return size, key, overlapped

#
# references: 
# * http://twistedmatrix.com/trac/browser/trunk/twisted/internet/iocpreactor/iocpsupport/wsarecv.pxi
# * http://www.google.com/codesearch/p?hl=en#T4zviHTmECg/trunk/exeLearning/twisted/internet/iocpreactor/_iocp.c&q=WSASendTo%20lang:python&d=5&l=348
#
winsockdll = None
def _init_winsockdll():
    global winsockdll
    if not winsockdll:
        winsockdll = ctypes.WinDLL("Ws2_32.dll")

def WSASendTo():
    _init_winsockdll()

def WSARecvFrom():
    _init_winsockdll()




