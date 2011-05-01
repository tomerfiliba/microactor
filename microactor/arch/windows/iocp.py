import os
import time
import itertools
import win32api
import win32file
import win32pipe
import win32con


IGNORED_ERRORS = (
    109,    # ERROR_BROKEN_PIPE
    232,    # ERROR_NO_DATA "The pipe is being closed"
    38,     # ERROR_HANDLE_EOF
)

EOF_ERRORS = (
    995,    # WSA_OPERATION_ABORTED
)

if not hasattr(win32file, "CreateIoCompletionPort"):
    raise ImportError("win32file is missing CreateIoCompletionPort")

class IOCP(object):
    def __init__(self):
        self._port = win32file.CreateIoCompletionPort(win32file.INVALID_HANDLE_VALUE, 
            None, 0, 0)
        self._post_overlapped = win32file.OVERLAPPED()
        self._handles = set()
    def __repr__(self):
        return "IOCP(%r)" % (self._port,)
    
    def close(self):
        if self._port:
            self._port.close()
            self._port = None
    
    def register(self, handle):
        """registers the given handle with the IOCP. the handle cannot be 
        unregistered later. handle must be a windows handle, not a fileno"""
        if hasattr(handle, "handle"):
            handle = handle.handle
        if handle in self._handles:
            return
        win32file.CreateIoCompletionPort(handle, self._port, 0, 0)
        self._handles.add(handle)
    
    def unregister(self, handle):
        if hasattr(handle, "handle"):
            handle = handle.handle
        self._handles.discard(handle)
    
    def post(self):
        """will cause wait() to return with the given information"""
        win32file.PostQueuedCompletionStatus(self._port, 0, 0, self._post_overlapped)
    
    def wait_event(self, timeout):
        """returns (size, overlapped) on success, None on timeout"""
        rc, size, _, overlapped = win32file.GetQueuedCompletionStatus(
            self._port, int(timeout * 1000))
        if rc == win32con.WAIT_TIMEOUT:
            return None
        elif rc == 0:
            if overlapped is self._post_overlapped:
                # ignore the overlapped -- it's was enqueued by post()
                return None
            else:
                return size, overlapped
        elif rc in IGNORED_ERRORS:
            return size, overlapped
        elif rc in EOF_ERRORS:
            print "!! WSA_OPERATION_ABORTED", overlapped
            return 0, overlapped
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


def validate_handle(handle):
    try:
        win32api.GetHandleInformation(handle)
    except win32api.error as ex:
        if ex.winerror == 6: # ERROR_INVALID_HANDLE
            return False
        else:
            raise
    else:
        return True

_pipe_id_counter = itertools.count()

def create_overlapped_pipe():
    pipe_name = r"\\.\pipe\anon_%s_%s_%s" % (os.getpid(), time.time(), 
        _pipe_id_counter.next())
    FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000

    read_handle = win32pipe.CreateNamedPipe(pipe_name,
                         win32con.PIPE_ACCESS_INBOUND | 
                            win32con.FILE_FLAG_OVERLAPPED | FILE_FLAG_FIRST_PIPE_INSTANCE,
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


OPEN_MODE_TABLE = {
    "r" : (win32con.GENERIC_READ,                           win32con.OPEN_EXISTING, "r"),
    "r+" : (win32con.GENERIC_READ | win32con.GENERIC_WRITE, win32con.OPEN_EXISTING, "rw"),
    "w" : (win32con.GENERIC_WRITE,                          win32con.CREATE_ALWAYS, "w"),
    "w+" : (win32con.GENERIC_READ | win32con.GENERIC_WRITE, win32con.CREATE_ALWAYS, "rw"),
    "a" : (win32con.GENERIC_WRITE,                          win32con.OPEN_ALWAYS,   "w"),
    "a+" : (win32con.GENERIC_READ | win32con.GENERIC_WRITE, win32con.OPEN_ALWAYS,   "rw"),
}

class WinFile(object):
    def __init__(self, handle):
        self.handle = handle
    @classmethod
    def open(cls, filename, mode = "r"):
        mode2 = mode.lower().replace("b", "").replace("t", "")
        create_file_flags, disposition, access = OPEN_MODE_TABLE[mode2]
        handle = win32file.CreateFile(filename, 
            create_file_flags,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE,
            None, # security
            disposition,
            win32con.FILE_FLAG_OVERLAPPED,
            None, # template
        )
        fobj = cls(handle)
        if "a" in mode2:
            fobj.seek(0, 2)
        return fobj, access
    def fileno(self):
        return self.handle
    def close(self):
        if self.handle:
            self.handle.close()
            self.handle = None
    def seek(self, offset, whence = 0):
        if whence == 0:
            whence = win32file.FILE_BEGIN
        elif whence == 1:
            whence = win32file.FILE_CURRENT
        elif whence == 2:
            whence = win32file.FILE_END
        else:
            raise ValueError("invalid whence value %r" % (whence,))
        self.flush()
        win32file.SetFilePointer(self.handle, offset, whence)
    def tell(self):
        self.flush()
        return win32file.SetFilePointer(self.handle, 0, win32file.FILE_CURRENT)



if __name__ == "__main__":
    import socket, sys, msvcrt
    s=socket.socket()
    port=IOCP()
    #port.register(msvcrt.get_osfhandle(sys.stdin.fileno())) #(87, 'CreateIoCompletionPort', 'The parameter is incorrect.')
    port.register(s.fileno())
    #port.register(s.fileno()) #(87, 'CreateIoCompletionPort', 'The parameter is incorrect.')


    


