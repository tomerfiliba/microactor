import threading
from microactor.subsystems.base import Subsystem
from microactor.utils import Deferred


class ThreadingSubsystem(Subsystem):
    NAME = "threading"
    
    def _init(self):
        self.threads = set()
    
    def call(self, func, *args, **kwargs):
        dfr = Deferred()
        def wrapper():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(res)
            finally:
                self.threads.discard(thd)
        thd = threading.Thread(target = wrapper)
        self.threads.add(thd)
        thd.start()
        return dfr



