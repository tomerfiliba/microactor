import weakref
from .epolling import EpollReactor
from .selecting import SelectReactor
from .polling import PollReactor
from .kqueue import KqueueReactor
from .iocp import IocpReactor
from microactor.subsystems import ALL_SUBSYSTEMS, init_subsystems


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

def get_reactor(name = None, subsystems = ALL_SUBSYSTEMS):
    if name:
        factory = REACTORS[name]
    else:
        factory = get_reactor_factory()
    if not factory.supported():
        raise UnsupportedReactor("%r is not supported on this platform" % (factory,))
    reactor = factory()
    init_subsystems(weakref.proxy(reactor), subsystems)
    return reactor



