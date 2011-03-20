import select
from .base import BasePoller


class SelectPoller(BasePoller):
    def __init__(self):
        self.rfiles = set()
        self.wfiles = set()
    @classmethod
    def supported(cls):
        return hasattr(select, "select")
    
    def register_read(self, fileobj):
        self.rfiles.add(fileobj)
    def register_write(self, fileobj):
        self.wfiles.add(fileobj)
    def unregister_read(self, fileobj):
        self.rfiles.discard(fileobj)
    def unregister_write(self, fileobj):
        self.rfiles.discard(fileobj)

    def poll(self, timeout):
        rl, wl, _ = select.select(self.rfiles, self.wfiles, (), timeout)
        return rl, wl




