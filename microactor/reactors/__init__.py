from .base import BaseReactor, ReactorError
from .posix import SelectReactor,  PollReactor, EpollReactor, KqueueReactor


def get_reactor_factory():
    for cls in [EpollReactor, KqueueReactor, PollReactor, SelectReactor]:
        if cls.supported():
            return cls
    raise ReactorError("no reactor supports this platform")

def get_reactor():
    cls = get_reactor_factory()
    return SelectReactor()

