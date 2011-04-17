import os
import time
import itertools
import ctypes
import socket # to initialize winsock
import msvcrt
import win32file
import win32pipe
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
        elif rc == 109:
            # ERROR_BROKEN_PIPE
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

_pipe_id_counter = itertools.count()

def create_overlapped_pipe():
    pipe_name = r"\\.\pipe\anon_%s_%s_%s" % (os.getpid(), time.time(), _pipe_id_counter.next())
    FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000

    read_handle = win32pipe.CreateNamedPipe(pipe_name,
                         win32con.PIPE_ACCESS_INBOUND | win32con.FILE_FLAG_OVERLAPPED | FILE_FLAG_FIRST_PIPE_INSTANCE,
                         win32con.PIPE_TYPE_BYTE | win32con.PIPE_WAIT,
                         1,             # Number of pipes
                         16384,         # Out buffer size
                         16384,         # In buffer size
                         1000,          # Timeout in ms
                         None)

    write_handle = win32file.CreateFile(pipe_name,
                        win32con.GENERIC_WRITE,
                        0,              # No sharing
                        None,           # security
                        win32con.OPEN_EXISTING,
                        win32con.FILE_ATTRIBUTE_NORMAL | win32con.FILE_FLAG_OVERLAPPED,
                        None)           # Template file
    
    return read_handle, write_handle


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
    raise NotImplementedError()

def WSARecvFrom():
    _init_winsockdll()
    raise NotImplementedError()



if __name__ == "__main__":
    rh, wh = create_overlapped_pipe()
    print rh, wh
    print win32file.WriteFile(wh, "hello world", None)
    print win32file.ReadFile(rh, 100, None)



