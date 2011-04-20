"""
IOCP-enabled datagram-socket APIs (not exposed via win32file)

references: 
 * http://twistedmatrix.com/trac/browser/trunk/twisted/internet/iocpreactor/iocpsupport/wsarecv.pxi
 * http://www.google.com/codesearch/p?hl=en#T4zviHTmECg/trunk/exeLearning/twisted/internet/iocpreactor/_iocp.c&q=WSASendTo%20lang:python&d=5&l=348
"""
import ctypes
import socket # to initialize winsock

try:
    winsockdll = ctypes.WinDLL("Ws2_32.dll")
except WindowsError as ex:
    raise ImportError(str(ex))


def WSASendTo():
    raise NotImplementedError()

def WSARecvFrom():
    raise NotImplementedError()

