from .base import FakePoller
from .poll_poller import PollPoller, EpollPoller
from .select_poller import SelectPoller
from .kqueue_poller import KqueuePoller
from .iocp_poller import IocpPoller


def get_default_poller():
    for cls in [EpollPoller, KqueuePoller, IocpPoller, PollPoller, SelectPoller]:
        if cls.supported():
            return cls
    return FakePoller

