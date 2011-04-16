from .base import BaseReactor, ReactorError
from .selecting import SelectingReactor


def get_reactor():
    return SelectingReactor()
