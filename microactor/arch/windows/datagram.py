"""
IOCP-enabled datagram-socket APIs (not exposed via win32file)

references: 
 * http://twistedmatrix.com/trac/browser/trunk/twisted/internet/iocpreactor/iocpsupport/wsarecv.pxi
 * http://www.google.com/codesearch/p?hl=en#T4zviHTmECg/trunk/exeLearning/twisted/internet/iocpreactor/_iocp.c&q=WSASendTo%20lang:python&d=5&l=348
"""
import win32file
import ctypes
from ctypes import wintypes
import socket # to make sure winsock is initialized
import struct
from pywintypes import OVERLAPPEDType as PyOVERLAPPED, HANDLEType as PyHANDLE
PTR = ctypes.POINTER

try:
    winsockdll = ctypes.WinDLL("Ws2_32.dll")
except WindowsError as ex:
    raise ImportError(str(ex))


class OVERLAPPED(ctypes.Structure):
    _fields_ = [('Internal', ctypes.c_void_p),      # ULONG_PTR
                ('InternalHigh', ctypes.c_void_p),  # ULONG_PTR
                ('Offset', wintypes.DWORD),         # DWORD
                ('OffsetHight', wintypes.DWORD),    # DWORD
                ('hEvent', wintypes.HANDLE),        # HANDLE
                ]

class WSABUF(ctypes.Structure):
    _fields_ = [('len', ctypes.c_ulong),            # u_long
                ('buf', PTR(ctypes.c_char)),           # char FAR *
                ]

class SockAddrIP4(ctypes.Structure):
    _fields_ = [('sin_family', ctypes.c_short),     # short
                ('sin_port', ctypes.c_ushort),      # u_short
                ('sin_addr', ctypes.c_ulong),       # struct  in_addr
                #('sin_addr', ctypes.c_char * 4),    # struct  in_addr
                ('sin_zero', ctypes.c_char * 8),    # sin_zero[8]
                ]


def deref(addr, typ):
    return ctypes.cast(addr, PTR(typ)).contents

_overlapped_offset = None
def get_overlapped_offset():
    global _overlapped_offset
    if _overlapped_offset is not None:
        return _overlapped_offset
    ov = win32file.OVERLAPPED()
    MAGIC = 0xff314159 # use a very high number that couldn't possibly be a pointer
    ov.Internal = MAGIC
    raw = struct.pack("L", MAGIC)
    s = ctypes.string_at(id(ov), 40)
    _overlapped_offset = s.find(raw)
    assert _overlapped_offset > 0
    return _overlapped_offset

def get_inner_overlapped(ov):
    return deref(id(ov) + get_overlapped_offset(), OVERLAPPED)

_WSASendTo = winsockdll.WSASendTo
_WSASendTo.argtypes = [
    wintypes.HANDLE,                # SOCKET s,
    PTR(WSABUF),                    # LPWSABUF lpBuffers,
    wintypes.DWORD,                 # DWORD dwBufferCount -- must be 1
    PTR(wintypes.DWORD),            # OUT LPDWORD lpNumberOfBytesSent -- must be NULL
    wintypes.DWORD,                 # DWORD dwFlags
    PTR(SockAddrIP4),               # IN struct sockaddr *lpTo
    ctypes.c_int,                   # int iToLen
    PTR(OVERLAPPED),                # IN LPWSAOVERLAPPED lpOverlapped
    wintypes.DWORD,                 # IN LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine -- must be NULL
] 
_WSASendTo.restype = ctypes.c_int   # 0 means success

def WSASendTo(hsock, data, sockaddr, overlapped, dwFlags = 0):
    buf = WSABUF(len(data), data)
    if isinstance(hsock, PyHANDLE):
        hsock = hsock.handle
    if isinstance(overlapped, PyOVERLAPPED):
        overlapped = get_inner_overlapped(overlapped)
    
    rc = _WSASendTo(hsock, ctypes.byref(buf), 1, 0, dwFlags, 
        ctypes.byref(sockaddr), ctypes.sizeof(sockaddr), ctypes.byref(overlapped), 0)
    if rc != 0:
        raise ctypes.WinError()

def WSASendTo4(hsock, data, addr, overlapped, dwFlags = 0):
    host, port = addr
    sockaddr = SockAddrIP4()
    sockaddr.sin_family = socket.AF_INET
    sockaddr.sin_port = port
    sockaddr.sin_addr = socket.inet_aton(host)
    return WSASendTo(hsock, data, sockaddr, overlapped, dwFlags)


_WSARecvFrom = winsockdll.WSARecvFrom
_WSARecvFrom.argtypes = [
    wintypes.HANDLE,                # SOCKET s,
    PTR(WSABUF),                    # LPWSABUF lpBuffers,
    wintypes.DWORD,                 # DWORD dwBufferCount -- must be 1
    PTR(wintypes.DWORD),            # OUT LPDWORD lpNumberOfBytesSent -- must be NULL
    PTR(wintypes.DWORD),            # INOUT LPDWORD lpFlags
    PTR(SockAddrIP4),               # OUT struct sockaddr *lpFrom
    PTR(ctypes.c_int),              # INOUT LPINT lpFromlen
    PTR(OVERLAPPED),                # IN LPWSAOVERLAPPED lpOverlapped
    wintypes.DWORD,                 # IN LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine -- must be NULL
]
_WSARecvFrom.restype = ctypes.c_int # 0 means success 

def WSARecvFrom(hsock, count, sockaddr, overlapped, dwFlags = 0):
    data = ctypes.create_string_buffer(count)
    buf = WSABUF(count, data)
    sockaddr_len = ctypes.c_int(ctypes.sizeof(sockaddr))
    flags = wintypes.DWORD(dwFlags)
    sentcount = wintypes.DWORD(0)

    if isinstance(hsock, PyHANDLE):
        hsock = hsock.handle
    if isinstance(overlapped, PyOVERLAPPED):
        overlapped = get_inner_overlapped(overlapped)
    
    rc = _WSARecvFrom(hsock, ctypes.byref(buf), 1, ctypes.byref(sentcount),
        ctypes.byref(flags), ctypes.byref(sockaddr), ctypes.byref(sockaddr_len),
        ctypes.byref(overlapped), 0)
    error = ctypes.GetLastError()
    if rc != 0 and error != win32file.WSA_IO_PENDING:
        raise ctypes.WinError(error)
    return data

def WSARecvFrom4(hsock, count, overlapped, dwFlags = 0):
    sockaddr = SockAddrIP4(socket.AF_INET)
    data = WSARecvFrom(hsock, count, sockaddr, overlapped, dwFlags)
    return data, sockaddr


"""
_CreateIoCompletionPort = ctypes.windll.kernel32.CreateIoCompletionPort
_CreateIoCompletionPort.argtypes = [
    wintypes.HANDLE,                # HANDLE FileHandle
    wintypes.HANDLE,                # HANDLE ExistingCompletionPort
    PTR(ctypes.c_ulong),            # ULONG_PTR CompletionKey
    wintypes.DWORD,                 # DWORD NumberOfConcurrentThreads
]
_CreateIoCompletionPort.restype = wintypes.HANDLE

_GetQueuedCompletionStatus = ctypes.windll.kernel32.GetQueuedCompletionStatus
_GetQueuedCompletionStatus.argtypes = [
    wintypes.HANDLE,                # HANDLE CompletionPort
    PTR(wintypes.DWORD),            # OUT LPDWORD lpNumberOfBytes
    PTR(ctypes.c_ulong),            # OUT PULONG_PTR lpCompletionKey
    PTR(PTR(OVERLAPPED)),           # OUT LPOVERLAPPED *lpOverlapped
    wintypes.DWORD,                 # DWORD dwMilliseconds
]
_GetQueuedCompletionStatus.restype = wintypes.BOOL

class IOCP(object):
    def __init__(self):
        self.port = _CreateIoCompletionPort(win32file.INVALID_HANDLE_VALUE, None, 
            None, 0)
        if self.port == 0:
            raise ctypes.WinError()
    def register(self, handle):
        rc = _CreateIoCompletionPort(handle, self.port, None, 0)
        if rc == 0:
            raise ctypes.WinError()
    def wait(self, timeout):
        if timeout < 0:
            timeout = -1
        else:
            timeout = int(timeout * 1000)
        ov_ptr = PTR(OVERLAPPED)()
        key = wintypes.DWORD()
        size = wintypes.DWORD()
        rc = _GetQueuedCompletionStatus(self.port, ctypes.byref(size), 
            ctypes.byref(key), ctypes.byref(ov_ptr), timeout)
        if rc == 0:
            error = win32api.GetLastError()
            if error == 258:
                return None
            elif not ov_ptr:
                raise ctypes.WinError()
        else:
            error = 0
        return error, size.value, ov_ptr.contents
"""


if __name__ == "__main__":
    import threading
    from iocp import IOCP

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", 12345))
    
    pyov = win32file.OVERLAPPED()
    port = IOCP()
    port.register(s.fileno())
    data, sockaddr = WSARecvFrom4(s.fileno(), 1000, pyov)
    
    def tfunc():
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.sendto("dkfdsfjdsl",("localhost",12345))
    thd = threading.Thread(target = tfunc)
    thd.start()
    
    print "waiting for data"
    [(size, pyov2)] = port.get_events(20)
    print "got", repr(data[:size])



