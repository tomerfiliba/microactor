from .base import BaseReactor, ReactorError
from .posix import SelectReactor,  PollReactor, EpollReactor, KqueueReactor
from .windows import IocpReactor


def get_reactor_factory():
    for cls in [EpollReactor, KqueueReactor, IocpReactor, PollReactor, SelectReactor]:
        if cls.supported():
            return cls
    raise ReactorError("no reactor supports this platform")

def get_reactor():
    cls = get_reactor_factory()
    return cls()

