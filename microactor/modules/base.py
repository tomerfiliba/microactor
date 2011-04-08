import microactor


class Module(object):
    @microactor.reactive
    def load(self, reactor):
        raise NotImplementedError()

    @microactor.reactive
    def unload(self):
        raise NotImplementedError()


class TcpServer(Module):
    def __init__(self, port, client_handler, bindhost = "0.0.0.0"):
        self.port = port
        self.bindhost = bindhost
        self.active = False
        self.client_handler = client_handler
    
    @microactor.reactive
    def load(self, reactor):
        self.listener = yield reactor.net.listen_tcp(self.port, self.bindhost)
        self.active = True
        try:
            while True:
                sock = yield self.listener.accept()
                reactor.call(self.client_handler, sock)
        except Exception:
            if not self.active:
                pass
            else:
                raise

    @microactor.reactive
    def unload(self):
        self.active = False
        yield self.listener.close()    

