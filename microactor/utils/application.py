from microactor.utils.deferred import reactive


def cli_switch(names, types = (), mandatory = False, requires = (), excludes = ()):
    def deco(func):
        def wrapper(*args, **kwargs):
            pass
        return wrapper
    return deco


class Application(object):
    def __init__(self, reactor):
        self.reactor = reactor
    
    @reactive
    def main(self):
        raise NotImplementedError()


