import weakref
from .posix import EpollReactor, SelectReactor, PollReactor, KqueueReactor
from .windows import IocpReactor


class UnsupportedReactor(Exception):
    pass

REACTORS = {
    "epoll" : EpollReactor,
    "kqueue" : KqueueReactor,
    "iocp" : IocpReactor,
    "poll" : PollReactor,
    "select" : SelectReactor,
}

def get_reactor_factory():
    for cls in [EpollReactor, KqueueReactor, IocpReactor, PollReactor, SelectReactor]:
        if cls.supported():
            return cls
    raise UnsupportedReactor("none of the available reactors is supported on this platform")

the_reactor = None

def get_reactor(name = None):
    global the_reactor
    if the_reactor:
        return the_reactor
    if name:
        factory = REACTORS[name]
    else:
        factory = get_reactor_factory()
    if not factory.supported():
        raise UnsupportedReactor("%r is not supported on this platform" % (factory,))
    the_reactor = factory()
    return the_reactor



