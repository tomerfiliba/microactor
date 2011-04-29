"""
IOCP-enabled datagram-socket APIs (not exposed via win32file)

references: 
 * http://twistedmatrix.com/trac/browser/trunk/twisted/internet/iocpreactor/iocpsupport/wsarecv.pxi
 * http://www.google.com/codesearch/p?hl=en#T4zviHTmECg/trunk/exeLearning/twisted/internet/iocpreactor/_iocp.c&q=WSASendTo%20lang:python&d=5&l=348
"""
import win32file
import ctypes
from ctypes import wintypes
from ctypes import POINTER as PTR
import socket
import struct
from pywintypes import OVERLAPPEDType as PyOVERLAPPED, HANDLEType as PyHANDLE

try:
    winsockdll = ctypes.WinDLL("Ws2_32.dll")
except WindowsError as ex:
    raise ImportError(str(ex))


#===============================================================================
# Winsock Types
#===============================================================================
class OVERLAPPED(ctypes.Structure):
    _fields_ = [('Internal', ctypes.c_void_p),      # ULONG_PTR
                ('InternalHigh', ctypes.c_void_p),  # ULONG_PTR
                ('Offset', wintypes.DWORD),         # DWORD
                ('OffsetHight', wintypes.DWORD),    # DWORD
                ('hEvent', wintypes.HANDLE),        # HANDLE
                ]

class WSABUF(ctypes.Structure):
    _fields_ = [('len', ctypes.c_ulong),            # u_long
                ('buf', PTR(ctypes.c_char)),        # char FAR *
                ]

class BaseSockAddr(ctypes.Structure):
    FAMILY = None
    def __init__(self, *args, **kwargs):
        super(BaseSockAddr, self).__init__(self.FAMILY, *args, **kwargs)
    def __str__(self):
        return "%s:%s" % (self.addr_str, self.port)
    def _get_addr_str(self):
        return inet_ntop(self.family, self.addr)
    def _set_addr_str(self, addrstr):
        self.addr = inet_pton(self.family, addrstr)
    addr_str = property(_get_addr_str, _set_addr_str)
    

class SockAddrIP4(BaseSockAddr):
    FAMILY = socket.AF_INET
    _fields_ = [('family', ctypes.c_short),         # short
                ('port', ctypes.c_ushort),          # u_short
                ('addr', ctypes.c_char * 4),        # struct in_addr
                ('zero', ctypes.c_char * 8),        # sin_zero[8]
                ]

class SockAddrIP6(BaseSockAddr):
    FAMILY = socket.AF_INET6
    _fields_ = [('family', ctypes.c_short),         # short
                ('port', ctypes.c_ushort),          # u_short
                ('flowinfo', ctypes.c_ulong),       # u_long
                ('addr', ctypes.c_char * 16),       # struct in6_addr
                ('scope_id', ctypes.c_ulong),       # u_long
                ]

_overlapped_offset = None
def _get_overlapped_offset():
    global _overlapped_offset
    if _overlapped_offset is not None:
        return _overlapped_offset
    ov = win32file.OVERLAPPED()
    MAGIC = 0xff314159 # use a very high number that couldn't possibly be a pointer
    ov.Internal = MAGIC # this is the first DWORD of the struct
    raw = struct.pack("L", MAGIC)
    s = ctypes.string_at(id(ov), 40)
    _overlapped_offset = s.find(raw)
    assert _overlapped_offset > 0
    return _overlapped_offset

def _get_inner_overlapped(ov):
    addr = id(ov) + _get_overlapped_offset()
    return ctypes.cast(addr, PTR(OVERLAPPED)).contents

#===============================================================================
# InetPton
#===============================================================================
_inet_pton = winsockdll.inet_pton
_inet_pton.argtypes = [
    ctypes.c_int,                   # INT Family
    ctypes.c_char_p,                # PCTSTR pszAddrString
    ctypes.c_void_p,                # OUT PVOID pAddrBuf
]
_inet_pton.restype = ctypes.c_int   # 1 = success, 0 = error

def inet_pton(family, addrstr):
    """converts an IPv4 or IPv6 string to raw bytes"""
    if family == socket.AF_INET:
        addr = ctypes.create_string_buffer(4)
    elif family == socket.AF_INET6:
        addr = ctypes.create_string_buffer(16)
    if _inet_pton(family, addrstr, ctypes.byref(addr)) != 1:
        raise ctypes.WinError()
    return addr.raw

#===============================================================================
# InetNtop
#===============================================================================
_inet_ntop = winsockdll.inet_ntop
_inet_ntop.argtypes = [
    ctypes.c_int,                   # INT Family
    ctypes.c_char_p,                # PVOID pAddrBuf
    ctypes.c_char_p,                # OUT PTSTR pAddrString
    ctypes.c_size_t,                # size_t StringBufSize
]
_inet_ntop.restype = ctypes.c_void_p # NULL = error, othersize = success

def inet_ntop(family, addrbytes):
    """converts raw bytes into IPv4 or IPv6 string"""
    addrstr = ctypes.create_string_buffer(80) # at least 46 bytes for IPv6
    if not _inet_ntop(family, addrbytes, addrstr, ctypes.sizeof(addrstr)):
        raise ctypes.WinError()
    return addrstr.value

#===============================================================================
# WSASendTo
#===============================================================================
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
    """generic sendto (must pass a populated sockaddr object)"""
    buf = WSABUF(len(data), data)
    if isinstance(hsock, PyHANDLE):
        hsock = hsock.handle
    if isinstance(overlapped, PyOVERLAPPED):
        overlapped = _get_inner_overlapped(overlapped)
    
    rc = _WSASendTo(hsock, ctypes.byref(buf), 1, 0, dwFlags, 
        ctypes.byref(sockaddr), ctypes.sizeof(sockaddr), ctypes.byref(overlapped), 0)
    if rc != 0 and rc != win32file.WSA_IO_PENDING:
        raise ctypes.WinError()

def WSASendTo4(hsock, data, addr, overlapped, dwFlags = 0):
    """IPv4 sendto"""
    host, port = addr
    sockaddr = SockAddrIP4(port = port, addr = inet_pton(host))
    return WSASendTo(hsock, data, sockaddr, overlapped, dwFlags)

def WSASendTo6(hsock, data, addr, overlapped, dwFlags = 0):
    """IPv6 sendto"""
    host, port = addr
    sockaddr = SockAddrIP6(port = port, addr = inet_pton(host))
    return WSASendTo(hsock, data, sockaddr, overlapped, dwFlags)

#===============================================================================
# WSARecvFrom
#===============================================================================
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
    """generic recvfrom (must pass an initialized sockaddr object)"""

    data = ctypes.create_string_buffer(count)
    buf = WSABUF(count, data)
    sockaddr_len = ctypes.c_int(ctypes.sizeof(sockaddr))
    flags = wintypes.DWORD(dwFlags)
    sentcount = wintypes.DWORD(0)

    if isinstance(hsock, PyHANDLE):
        hsock = hsock.handle
    if isinstance(overlapped, PyOVERLAPPED):
        overlapped = _get_inner_overlapped(overlapped)
    
    rc = _WSARecvFrom(hsock, ctypes.byref(buf), 1, ctypes.byref(sentcount),
        ctypes.byref(flags), ctypes.byref(sockaddr), ctypes.byref(sockaddr_len),
        ctypes.byref(overlapped), 0)
    error = ctypes.GetLastError()
    if rc != 0 and error != win32file.WSA_IO_PENDING:
        raise ctypes.WinError(error)
    return data

def WSARecvFrom4(hsock, count, overlapped, dwFlags = 0):
    """IPv4 recvfrom"""
    sockaddr = SockAddrIP4()
    data = WSARecvFrom(hsock, count, sockaddr, overlapped, dwFlags)
    return data, sockaddr

def WSARecvFrom6(hsock, count, overlapped, dwFlags = 0):
    """IPv6 recvfrom"""
    sockaddr = SockAddrIP6()
    data = WSARecvFrom(hsock, count, sockaddr, overlapped, dwFlags)
    return data, sockaddr


#===============================================================================
# Test
#===============================================================================
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
    [(size, _)] = port.get_events(20)
    print "got", repr(data[:size]), "from", sockaddr



