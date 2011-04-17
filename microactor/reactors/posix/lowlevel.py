import fcntl
from array import array

# Linux
FIONREAD = 0x541B
TIOCOUTQ = 0x5411

def get_pending_read(fd):
    a = array("i", [0])
    fcntl.ioctl(fd, FIONREAD, a, True)
    return a[0]

def get_pending_write(fd):
    a = array("i", [0])
    fcntl.ioctl(fd, TIOCOUTQ, a, True)
    return a[0]

