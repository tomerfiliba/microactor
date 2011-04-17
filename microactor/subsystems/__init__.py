from .base import Subsystem
from .threads import ThreadPoolSubsystem
from .jobs import JobSubsystem
from .processes import ProcessSubsystem

GENERIC_SUBSYSTEMS = [JobSubsystem, ThreadPoolSubsystem, ProcessSubsystem]
