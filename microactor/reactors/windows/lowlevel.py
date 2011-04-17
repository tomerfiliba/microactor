import itertools
import ctypes
import socket # to initialize winsock
import msvcrt
import win32file
import win32con
import time
#import pywintypes


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
        unregistered later"""
        if hasattr(handle, "fileno"):
            handle = handle.fileno()
            try:
                handle = msvcrt.get_osfhandle(handle)
            except IOError:
                pass
        key = self._key.next()
        win32file.CreateIoCompletionPort(handle, self._port, key, 0)
        return key
    
    def post(self, key = None, size = 0, overlapped = None):
        """will cause wait() to return with the given information"""
        if key is None:
            key = self._post_key
        win32file.PostQueuedCompletionStatus(self._port, size, key, overlapped)
    
    def wait_event(self, timeout):
        """returns (size, overlapped) on success, None on timeout"""
        rc, size, _, overlapped = win32file.GetQueuedCompletionStatus(
            self._port, int(timeout * 1000))
        if rc == win32con.WAIT_TIMEOUT:
            return None
        elif rc == 0:
            return size, overlapped
        else:
            ex = WindowsError(rc)
            ex.errno = ex.winerror = rc
            raise ex
    
    def get_events(self, timeout):
        events = []
        tmax = time.time() + timeout
        while True:
            res = self.wait_event(timeout)
            if not res:
                break
            events.append(res)
            timeout = 0
            if time.time() > tmax:
                break
        return events        


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







