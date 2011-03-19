from .polling import DEFAULT_POLLER


class Reactor(object):
    def __init__(self, poller_factory = DEFAULT_POLLER):
        self._poller = poller_factory()
        self._tasks = []
        self._active = False
    
    def start(self):
        assert not self._active
        self._active = True
        while self._active:
            self._work()
    
    def stop(self):
        assert self._active
        self._active = False
    
    def _work(self):
        pass

    ###########################################################################
    # tasks
    ###########################################################################
    def register_task(self, task):
        pass
    def call(self, func, args = (), kwargs = {}):
        return self.call_within(0, func, args, kwargs)
    def call_within(self, delay, func, args = (), kwargs = {}):
        pass
    def call_every(self, interval, func, args = (), kwargs = {}):
        pass

