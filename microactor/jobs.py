import time


class SingleJob(object):
    __slots__ = ["_timestamp", "_callback", "_overdue_threshold", "_active"]
    def __init__(self, timestamp, callback):
        self._timestamp = timestamp
        self._callback = callback
        self._active = True
        self._overdue_threshold = None
    def get_timestamp(self):
        return self._timestamp
    def cancel(self):
        self._active = False
    def invoke(self, now):
        if not self._active:
            return
        if self._overdue_threshold is not None and now - self._overdue_threshold > self._timestamp:
            return
        self._callback()

class PeriodicJob(SingleJob):
    __slots__ = ["_t0", "interval"]
    def __init__(self, interval, callback):
        self._t0 = time.time()
        self.interval = interval
        PeriodicJob.__init__(None, callback)
        self._overdue_threshold = True
    
    def get_timestamp(self, now):
        return self._t0 + (((now - self._t0) // self.interval) + 1) * self.interval




