import time
import functools
from .base import Subsystem
from microactor.utils import ReactorDeferred, reactive, rreturn


class JobSubsystem(Subsystem):
    NAME = "jobs"
    
    def sleep(self, interval):
        return self.schedule(interval, lambda: None)
    
    def schedule(self, interval, func, *args, **kwargs):
        def wrapper():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(res)
        
        functools.update_wrapper(wrapper, func)
        dfr = ReactorDeferred(self.reactor)
        self.reactor.call_at(time.time() + interval, wrapper)
        return dfr
    
    def schedule_every(self, interval, func, *args, **kwargs):
        def wrapper():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                dfr.throw(ex)
            else:
                if res is False:
                    dfr.set()
                else:
                    ts = t0 + (((time.time() - t0) // interval) + 1) * interval
                    self.reactor.call_at(ts, wrapper)
        
        functools.update_wrapper(wrapper, func)
        dfr = ReactorDeferred(self.reactor)
        t0 = time.time()
        self.reactor.call_at(t0, wrapper)
        return dfr

    @reactive
    def joined(self, dfrlist):
        reslist = []
        for dfr in dfrlist:
            res = yield dfr
            reslist.append(res)
        rreturn(reslist)


