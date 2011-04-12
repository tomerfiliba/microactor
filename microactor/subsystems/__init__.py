from .base import Subsystem
from .jobs import JobSubsystem
from .files import FilesSubsystem
from .processing import ProcessSubsystem
from .threads import ThreadingSubsystem
from .http import HttpSubsystem
from .ssh import SshSubsystem
from .rpc import RpcSubsystem


GENERIC_SUBSYSTEMS = [JobSubsystem, FilesSubsystem, ProcessSubsystem, 
    ThreadingSubsystem, HttpSubsystem, SshSubsystem, RpcSubsystem]

