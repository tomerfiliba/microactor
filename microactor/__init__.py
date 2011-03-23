from .reactors import get_reactor_factory
from .utils import reactive, Deferred, rreturn


def get_reactor():
    return get_reactor_factory()()

