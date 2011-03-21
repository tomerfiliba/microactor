class BaseJob(object):
    def __init__(self, reactor, func):
        self.reactor = reactor
        self.func = func
        self._canceled = False
    def cancel(self):
        self._canceled = True
    def canceled(self):
        return self._canceled
    def get_timestamp(self, now):
        raise NotImplementedError()
    def __call__(self, now):
        if self._canceled:
            return
        self.func(self)

class SingleJob(BaseJob):
    def __init__(self, reactor, func, timestamp):
        BaseJob.__init__(self, reactor, func)
        self._timestamp = timestamp
    def get_timestamp(self, now):
        return self._timestamp

class PeriodicJob(BaseJob):
    def __init__(self, reactor, func, t0, interval):
        BaseJob.__init__(self, reactor, func)
        self._t0 = t0
        self.interval = interval
    def get_timestamp(self, now):
        return self._t0 + (((now - self._t0) // self.interval) + 1) * self.interval
    def __call__(self, now):
        BaseJob.__call__(self, now)
        if not self._canceled:
            self.reactor.add_job(self)










    