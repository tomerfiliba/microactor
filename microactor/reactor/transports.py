class BaseTransport(object):
    def write(self):
        pass


class StreamTransport(object):
    def __init__(self, reactor, fileobj):
        self.reactor = reactor
        self._writebuf = ""
    def write(self, data):
        self._writebuf += data
        self.reactor.register_write(self, self.on_write)
    def on_write(self):
        pass


class SocketTransport(object):
    def __init__(self):
        pass
