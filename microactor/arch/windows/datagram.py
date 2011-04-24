"""
IOCP-enabled datagram-socket APIs (not exposed via win32file)

references: 
 * http://twistedmatrix.com/trac/browser/trunk/twisted/internet/iocpreactor/iocpsupport/wsarecv.pxi
 * http://www.google.com/codesearch/p?hl=en#T4zviHTmECg/trunk/exeLearning/twisted/internet/iocpreactor/_iocp.c&q=WSASendTo%20lang:python&d=5&l=348
"""
import win32api
import win32file
import ctypes
from ctypes import wintypes
import socket # to make sure winsock is initialized

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
                ('buf', ctypes.POINTER(ctypes.c_char)),           # char FAR *
                ]

class SockAddrIP4(ctypes.Structure):
    _fields_ = [('sin_family', ctypes.c_short),     # short
                ('sin_port', ctypes.c_ushort),      # u_short
                ('sin_addr', ctypes.c_ulong),       # struct  in_addr
                ('sin_zero', ctypes.c_char * 8),    # sin_zero[8]
                ]

_WSASendTo = winsockdll.WSASendTo
_WSASendTo.argtypes = [
    wintypes.HANDLE,                # SOCKET s,
    ctypes.POINTER(WSABUF),         # LPWSABUF lpBuffers,
    wintypes.DWORD,                 # DWORD dwBufferCount -- must be 1
    ctypes.POINTER(wintypes.DWORD), # OUT LPDWORD lpNumberOfBytesSent -- must be NULL
    wintypes.DWORD,                 # DWORD dwFlags
    ctypes.POINTER(SockAddrIP4),    # IN struct sockaddr *lpTo
    ctypes.c_int,                   # int iToLen
    ctypes.POINTER(OVERLAPPED),     # IN LPWSAOVERLAPPED lpOverlapped
    wintypes.DWORD,                 # IN LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine -- must be NULL
] 
_WSASendTo.restype = ctypes.c_int   # 0 means success

def WSASendTo(hsock, data, addr, overlapped, dwFlags = 0):
    buf = WSABUF(len(data), data)
    host, port = addr
    sockaddr = SockAddrIP4()
    sockaddr.sin_family = socket.AF_INET
    sockaddr.sin_port = port
    sockaddr.sin_addr = socket.inet_aton(host)
    
    rc = _WSASendTo(hsock, ctypes.byref(buf), 1, 0, dwFlags, 
        ctypes.byref(sockaddr), ctypes.sizeof(sockaddr), ctypes.byref(overlapped), 0)
    if rc != 0:
        raise ctypes.WinError()


_WSARecvFrom = winsockdll.WSARecvFrom
_WSARecvFrom.argtypes = [
    wintypes.HANDLE,                # SOCKET s,
    ctypes.POINTER(WSABUF),         # LPWSABUF lpBuffers,
    wintypes.DWORD,                 # DWORD dwBufferCount -- must be 1
    ctypes.POINTER(wintypes.DWORD), # OUT LPDWORD lpNumberOfBytesSent -- must be NULL
    ctypes.POINTER(wintypes.DWORD), # INOUT LPDWORD lpFlags
    ctypes.POINTER(SockAddrIP4),    # OUT struct sockaddr *lpFrom
    ctypes.POINTER(ctypes.c_int),   # INOUT LPINT lpFromlen
    ctypes.POINTER(OVERLAPPED),     # IN LPWSAOVERLAPPED lpOverlapped
    wintypes.DWORD,                 # IN LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine -- must be NULL
]
_WSARecvFrom.restype = ctypes.c_int # 0 means success 

def WSARecvFrom(hsock, count, overlapped, dwFlags = 0):
    data = ctypes.create_string_buffer(count)
    buf = WSABUF(count, data)
    sockaddr = SockAddrIP4(socket.AF_INET)
    sockaddr_len = ctypes.c_int(ctypes.sizeof(sockaddr))
    flags = wintypes.DWORD(dwFlags)
    sentcount = wintypes.DWORD(0)
    
    rc = _WSARecvFrom(hsock, ctypes.byref(buf), 1, ctypes.byref(sentcount),
        ctypes.byref(flags), ctypes.byref(sockaddr), ctypes.byref(sockaddr_len),
        ctypes.byref(overlapped), 0)
    error = win32api.GetLastError()
    if rc != 0 and error != win32file.WSA_IO_PENDING:
        raise ctypes.WinError(error)
    return data, sockaddr



if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", 12345))
    from iocp import IOCP
    ov = win32file.OVERLAPPED()
    #ov = OVERLAPPED()
    port = IOCP()
    port.register(s.fileno())
    data, sockaddr = WSARecvFrom(s.fileno(), 1000, ov)
    print port.wait_event(10)




