from .base import Subsystem
from .threads import ThreadPoolSubsystem
from .jobs import JobSubsystem

GENERIC_SUBSYSTEMS = [ThreadPoolSubsystem, JobSubsystem]
