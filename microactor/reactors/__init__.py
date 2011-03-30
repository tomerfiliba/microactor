import weakref
from .epolling import EpollReactor
from .selecting import SelectReactor
from .polling import PollReactor
from .kqueue import KqueueReactor
from .iocp import IocpReactor
from microactor.subsystems import ALL_SUBSYSTEMS, init_subsystems


class NoSupportedReactor(Exception):
    pass

def get_reactor_factory():
    for cls in [EpollReactor, KqueueReactor, PollReactor, IocpReactor, SelectReactor]:
        if cls.supported():
            return cls
    raise NoSupportedReactor("none of the available reactors is supported on this platform")

def get_reactor(subsystems = ALL_SUBSYSTEMS):
    factory = get_reactor_factory()
    reactor = factory()
    init_subsystems(weakref.proxy(reactor), subsystems)
    return reactor



