from . import polling



class Reactor(object):
    def __init__(self, poller_factory = polling.DEFAULT_POLLER):
        self._poller = poller_factory()
        self._call_queue = []
        self._processes = []
        self._active = False
    
    def main(self):
        assert self._active
        self._active = True
        while self._active:
            pass
    
    def close(self):
        if not self._active:
            return
        self._active = False
        self._poller.close()


