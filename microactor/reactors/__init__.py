class NoSupportedReactor(Exception):
    pass

def get_reactor_factory():
    from .epolling import EpollReactor
    from .selecting import SelectReactor
    from .polling import PollReactor
    for cls in [EpollReactor, SelectReactor, PollReactor]:
        if cls.supported():
            return cls
    raise NoSupportedReactor()



