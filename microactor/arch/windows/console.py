import win32console
import win32event
from contextlib import contextmanager


class Cursor(object):
    __slots__ = ["outbuf"]
    COLOR_NAMES = dict(
        black = 0,
        blue = 1,
        green = 2,
        cyan = 3,
        red = 4,
        magenta = 5,
        yellow = 6,
        white = 7,
        gray = 8,
        bright_blue = 9,
        bright_green = 10,
        bright_cyan = 11,
        bright_red = 12,
        bright_magenta = 13,
        bright_yellow = 14,
        bright_white = 15,
    )
    REV_COLOR_NAMES = dict((v, k) for k, v in COLOR_NAMES.items())
    COLOR_NAMES["grey"] = COLOR_NAMES["gray"]
    
    def __init__(self, outbuf):
        self.outbuf = outbuf
    def get_position(self):
        info = self.outbuf.GetConsoleScreenBufferInfo()
        cp = info["CursorPosition"]
        return (cp.X, cp.Y)
    def move(self, x, y):
        self.outbuf.SetConsoleCursorPosition(win32console.PyCOORDType(x, y))
    def show(self):
        size, _ = self.outbuf.GetConsoleCursorInfo()
        self.outbuf.SetConsoleCursorInfo(size, True)
    def hide(self):
        size, _ = self.outbuf.GetConsoleCursorInfo()
        self.outbuf.SetConsoleCursorInfo(size, False)
    def get_color(self):
        flags = self.get_attributes()
        fg = flags & 0xf
        bg = (flags >> 4) & 0xf
        return self.REV_COLOR_NAMES[fg], self.REV_COLOR_NAMES[bg]
    def set_color(self, fg = None, bg = None):
        curr_fg, curr_bg = self.get_color()
        if fg is None:
            fg = curr_fg
        if bg is None:
            bg = curr_bg
        fg = self.COLOR_NAMES[fg]
        bg = self.COLOR_NAMES[bg] << 4
        flags = self.get_attributes()
        self.set_attributes((flags & ~0xff) | fg | bg)
    def set_attributes(self, flags):
        self.outbuf.SetConsoleTextAttribute(flags)
    def get_attributes(self):
        info = self.outbuf.GetConsoleScreenBufferInfo()
        return info["Attributes"]
    def write(self, text, pos = (), fg = None, bg = None):
        if fg or bg:
            self.set_color(fg, bg)
        if pos:
            self.move(*pos)
        return self.outbuf.WriteConsole(text)

class Screen(object):
    __slots__ = ["outbuf"]
    def __init__(self, outbuf):
        self.outbuf = outbuf
    def get_virtual_size(self):
        info = self.outbuf.GetConsoleScreenBufferInfo()
        s = info["Size"]
        return (s.X, s.Y)
    def get_size(self):
        info = self.outbuf.GetConsoleScreenBufferInfo()
        s = info["MaximumWindowSize"]
        return (s.X, s.Y)
    def clear(self, fg = "white", bg = "black"):
        x, y = self.get_size()
        self.outbuf.FillConsoleOutputCharacter(u" ", x * y,
            win32console.PyCOORDType(0, 0))
        flags = Cursor.COLOR_NAMES[fg] | (Cursor.COLOR_NAMES[bg] << 4) 
        self.outbuf.FillConsoleOutputAttribute(flags, x * y, 
            win32console.PyCOORDType(0, 0))
        self.outbuf.SetConsoleCursorPosition(win32console.PyCOORDType(0, 0))
    def scroll(self, num_of_lines):
        raise NotImplementedError()
    def set_title(self, text):
        win32console.SetConsoleTitle(text)
    def get_title(self):
        return win32console.GetConsoleTitle()

class ConsoleError(OSError):
    pass

class Console(object):
    def __init__(self):
        self.inbuf = None
        if not self.is_attached():
            raise ConsoleError("process not attached to a console")
        self.inbuf = win32console.PyConsoleScreenBufferType(
            win32console.GetStdHandle(win32console.STD_INPUT_HANDLE))
        self.outbuf = win32console.PyConsoleScreenBufferType(
            win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE))
        self.clear_events()
        self.cursor = Cursor(self.outbuf)
        self.screen = Screen(self.outbuf)
        self._orig_mode = self.inbuf.GetConsoleMode()
        self._orig_attrs = self.cursor.get_attributes()
        self.inbuf.SetConsoleMode(self._orig_mode & 
            ~win32console.ENABLE_LINE_INPUT & 
            ~win32console.ENABLE_ECHO_INPUT & 
            ~win32console.ENABLE_PROCESSED_INPUT)
    
    def __del__(self):
        self.close()
    def close(self):
        if not self.inbuf:
            return
        self.inbuf.SetConsoleMode(self._orig_mode)
        self.cursor.set_attributes(self._orig_attrs)            
        self.inbuf.close()
        self.inbuf = None
        self.outbuf.close()
        self.outbuf = None
        
    @classmethod
    def allocate(cls):
        win32console.AllocConsole()
    
    @classmethod
    def is_attached(cls):
        return win32console.GetConsoleWindow() != 0
    
    def get_events(self):
        return self.inbuf.ReadConsoleInput(100)
    def get_num_of_events(self):
        return self.inbuf.GetNumberOfConsoleInputEvents()
    def clear_events(self):
        self.inbuf.FlushConsoleInputBuffer()
    def read(self, count):
        return self.inbuf.ReadConsole(count)
    def write(self, text):
        return self.outbuf.WriteConsole(text)
    def wait_input(self, timeout = None):
        if timeout is None or timeout < 0:
            timeout = -1    # INFITINE
        else:
            timeout = int(timeout * 1000)
        rc = win32event.WaitForSingleObject(self.inbuf, timeout)
        return rc == win32event.WAIT_OBJECT_0


if __name__ == "__main__":
    import os, sys
    con = Console()
    ch = os.read(sys.stdin.fileno(), 1)
    print "got", ch







