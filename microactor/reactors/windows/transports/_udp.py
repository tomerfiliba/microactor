"""
references: 
* http://twistedmatrix.com/trac/browser/trunk/twisted/internet/iocpreactor/iocpsupport/wsarecv.pxi
* http://www.google.com/codesearch/p?hl=en#T4zviHTmECg/trunk/exeLearning/twisted/internet/iocpreactor/_iocp.c&q=WSASendTo%20lang:python&d=5&l=348
"""
import ctypes

winsockdll = None
def _init_winsockdll():
    global winsockdll
    if not winsockdll:
        winsockdll = ctypes.WinDLL("Ws2_32")

def WSASendTo():
    _init_winsockdll()

def WSARecvFrom():
    _init_winsockdll()




