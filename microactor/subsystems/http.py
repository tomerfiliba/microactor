from .base import Subsystem

class HttpRequest(object):
    __slots__ = []

class HttpConnection(object):
    __slots__ = []

class HttpProcessor(object):
    pass



class HttpSubsystem(Subsystem):
    NAME = "http"
    
    def connect(self, url):
        pass

