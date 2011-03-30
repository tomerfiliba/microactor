from .base import Subsystem
from microactor.utils import Deferred
import time


class JobSubsystem(Subsystem):
    NAME = "jobs"
    
    def sleep(self, interval):
        return self.schedule(interval, lambda: None)
    
    def schedule(self, interval, func, *args, **kwargs):
        dfr = Deferred()
        def invocation():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(res)
        
        self.reactor.add_job(time.time() + interval, invocation)
        return dfr

    def schedule_every(self, interval, func, *args, **kwargs):
        dfr = Deferred()
        def invocation():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                dfr.throw(ex)
            else:
                if res is False:
                    dfr.set()
                else:
                    ts = t0 + (((time.time() - t0) // interval) + 1) * interval
                    self.reactor.add_job(ts, invocation)
        
        t0 = time.time()
        self.reactor.add_job(t0, invocation)
        return dfr





