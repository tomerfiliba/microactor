import weakref
import threading
import win32api
import win32console
import win32event
from microactor.utils import ReactorDeferred


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
    def __init__(self, reactor):
        if not self.is_attached():
            raise ValueError("process not attached to a console")
        self.inbuf = win32console.PyConsoleScreenBufferType(
            win32api.GetStdHandle(win32api.STD_INPUT_HANDLE))
        self.outbuf = win32console.PyConsoleScreenBufferType(
            win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE))
        self.clear_events()
        self.cursor = Cursor(weakref.proxy(self))
        self.screen = Screen(weakref.proxy(self))
        self.reactor = reactor
        self._events = []
        self._event_dfr = None
        self._active = True
        self._closed_dfr = ReactorDeferred(self.reactor)
        self._orig_mode = self.inbuf.GetConsoleMode()
        self._orig_attrs = self.cursor.get_attributes()
        self.inbuf.SetConsoleMode(self._orig_mode & 
            ~win32console.ENABLE_LINE_INPUT & 
            ~win32console.ENABLE_ECHO_INPUT & 
            ~win32console.ENABLE_PROCESSED_INPUT)
        self._thd = threading.Thread(name="ConsoleInputThread", target = self._input_watcher_thread)
        self._thd.start()
    
    def __enter__(self):
        return self
    def __exit__(self, t, v, tb):
        self.close()
    def __del__(self):
        self.close()
    
    def close(self):
        if not self._active:
            self._active = False
            self.inbuf.SetConsoleMode(self._orig_mode)
            self.cursor.set_attributes(self._orig_attrs)
        return self._closed_dfr
    
    @classmethod
    def allocate(cls):
        win32console.AllocConsole()
    
    @classmethod
    def is_attached(cls):
        return win32console.GetConsoleWindow() != 0
       
    def _get_events(self):
        return self.inbuf.ReadConsoleInput(100)
    def _get_num_of_events(self):
        return self.inbuf.GetNumberOfConsoleInputEvents()
    def clear_events(self):
        self.inbuf.FlushConsoleInputBuffer()
    
    def read_event(self):
        if self._event_dfr:
            raise ValueError("overlapping read")
        event_dfr = ReactorDeferred(self.reactor)
        if self._events:
            evt = self._events.pop(0)
            event_dfr.set(evt)
        else:
            self._event_dfr = event_dfr
        return event_dfr
    
    def write(self, text, pos = None, fg = None, bg = None):
        if pos:
            x, y = pos
            self.cursor.move(x, y)
        if fg or bg:
            self.cursor.set_color(fg, bg)
        self.outbuf.WriteConsole(text)
    
    def on_input(self):
        if self._get_num_of_events() <= 0:
            return
        self._events.extend(self._get_events())
        if self._event_dfr and not self._event_dfr.is_set():
            evt = self._events.pop(0) if self.events else None
            self._event_dfr.set(evt)
            self._event_dfr = None
    
    def _input_watcher_thread(self):
        try:
            while self._active:
                rc = win32event.WaitForSingleObject(self.inbuf, 200) # 0.2 sec
                if rc == win32event.WAIT_OBJECT_0:
                    self.reactor.call(self.on_input)
                    self.reactor._wakeup()
        finally:
            self._closed_dfr.set()



if __name__ == "__main__":
    con = Console(None)
    
    with con.raw_mode():
        con.screen.clear(bg="gray")
        con.write("hello world\n", (10, 5), fg = "bright_red")
        print win32event.WaitForSingleObject(con.inbuf, 10000)

        for i in range(10):
            e = con.read()
            con.write(repr(e) + "\n", fg = "white")






