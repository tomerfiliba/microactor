import microactor


class Module(object):
    @microactor.reactive
    def start(self, reactor):
        raise NotImplementedError()    

    def stop(self):
        raise NotImplementedError()    



