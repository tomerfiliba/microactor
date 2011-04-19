import win32api
import win32console
from contextlib import contextmanager
import win32event


class Cursor(object):
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
        grey = 8,
        bright_blue = 9,
        bright_green = 10,
        bright_cyan = 11,
        bright_red = 12,
        bright_magenta = 13,
        bright_yellow = 14,
        bright_white = 15,
    )
    REV_COLOR_NAMES = dict((v, k) for k, v in COLOR_NAMES.items())
    
    def __init__(self, con):
        self.con = con
    def get_position(self):
        info = self.con.outbuf.GetConsoleScreenBufferInfo()
        cp = info["CursorPosition"]
        return (cp.X, cp.Y)
    def move(self, x, y):
        self.con.outbuf.SetConsoleCursorPosition(win32console.PyCOORDType(x,y))
    def show(self):
        size, _ = self.con.outbuf.GetConsoleCursorInfo()
        self.con.outbuf.SetConsoleCursorInfo(size, True)
    def hide(self):
        size, _ = self.con.outbuf.GetConsoleCursorInfo()
        self.con.outbuf.SetConsoleCursorInfo(size, False)
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
        self.con.outbuf.SetConsoleTextAttribute(flags)
    def get_attributes(self):
        info = self.con.outbuf.GetConsoleScreenBufferInfo()
        return info["Attributes"]

class Screen(object):
    def __init__(self, con):
        self.con = con
    def get_virtual_size(self):
        info = self.con.outbuf.GetConsoleScreenBufferInfo()
        s = info["Size"]
        return (s.X, s.Y)
    def get_size(self):
        info = self.con.outbuf.GetConsoleScreenBufferInfo()
        s = info["MaximumWindowSize"]
        return (s.X, s.Y)
    def clear(self, fg = "white", bg = "black"):
        x, y = self.get_size()
        self.con.outbuf.FillConsoleOutputCharacter(u" ", x * y,
            win32console.PyCOORDType(0, 0))
        flags = Cursor.COLOR_NAMES[fg] | (Cursor.COLOR_NAMES[bg] << 4) 
        self.con.outbuf.FillConsoleOutputAttribute(flags, x * y, 
            win32console.PyCOORDType(0, 0))
        self.con.cursor.move(0, 0)
    def scroll(self, num_of_lines):
        raise NotImplementedError()
    def set_title(self, text):
        win32console.SetConsoleTitle(text)
    def get_title(self):
        return win32console.GetConsoleTitle()


class Console(object):
    def __init__(self):
        self.inbuf = win32console.PyConsoleScreenBufferType(
            win32api.GetStdHandle(win32api.STD_INPUT_HANDLE))
        self.outbuf = win32console.PyConsoleScreenBufferType(
            win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE))
        self.clear_events()
        self.cursor = Cursor(self)
        self.screen = Screen(self)
    
    @contextmanager
    def raw_mode(self):
        mode = self.inbuf.GetConsoleMode()
        mode2 = (mode & ~win32console.ENABLE_LINE_INPUT & 
            ~win32console.ENABLE_ECHO_INPUT & ~win32console.ENABLE_PROCESSED_INPUT)
        self.inbuf.SetConsoleMode(mode2)
        attrs = self.cursor.get_attributes()
        try:
            yield
        finally:
            self.inbuf.SetConsoleMode(mode)
            self.cursor.set_attributes(attrs)
    
    def get_events(self):
        return self.inbuf.ReadConsoleInput(100)
    def get_num_of_events(self):
        return self.inbuf.GetNumberOfConsoleInputEvents()
    def clear_events(self):
        self.inbuf.FlushConsoleInputBuffer()
    def read(self):
        return self.inbuf.ReadConsole(100)
    def write(self, text, pos = None, fg = None, bg = None):
        if pos:
            x, y = pos
            self.cursor.move(x, y)
        if fg or bg:
            self.cursor.set_color(fg, bg)
        self.outbuf.WriteConsole(text)
    


if __name__ == "__main__":
    con = Console()
    print "events", con.get_num_of_events()
    print win32event.WaitForSingleObject(con.inbuf, 1000)
    
    with con.raw_mode():
        con.screen.clear(b="gray")
        con.write("hello world\n", (10, 5), fg = "bright_red")
        for i in range(10):
            e = con.read()
            con.write(repr(e) + "\n", fg = "white")






