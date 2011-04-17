from .base import Subsystem
from .threadpool import ThreadPoolSubsystem
from .jobs import JobSubsystem

GENERIC_SUBSYSTEMS = [ThreadPoolSubsystem, JobSubsystem]
