import sys
import os
import signal
import subprocess
from .base import Subsystem
from microactor.utils import ReactorDeferred, reactive, rreturn
from microactor.utils import BufferedTransport, safe_import
windows = safe_import("microactor.utils.windows")
msvcrt = safe_import("msvcrt")


if sys.platform == "win32":
    # god bless monkey patching
    import _subprocess
    _subprocess.CreatePipe = lambda a, b: windows.create_overlapped_pipe()


class ProcessExecutionError(Exception):
    def __init__(self, msg, rc, stdout, stderr):
        Exception.__init__(self, msg, rc, stdout, stderr)
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr


class Process(object):
    def __init__(self, reactor, proc, cmdline):
        self.reactor = reactor
        self.cmdline = cmdline
        self._proc = proc
        self.stdin = BufferedTransport(self.reactor._io.wrap_pipe(proc.stdin, "w"))
        self.stdout = BufferedTransport(self.reactor._io.wrap_pipe(proc.stdout, "r"))
        self.stderr = BufferedTransport(self.reactor._io.wrap_pipe(proc.stderr, "r"))
        self.pid = proc.pid
        self.wait_dfr = ReactorDeferred(self.reactor)
    def __repr__(self):
        return "<Process %r: %r (%s)>" % (self.pid, self.cmdline, 
            "alive" if self.is_alive() else "dead")
    def on_termination(self):
        self.wait_dfr.set(self.returncode)
    @property
    def returncode(self):
        return self._proc.returncode
    def is_alive(self):
        return self._proc.poll() is None
    def signal(self, sig):
        self._proc.send_signal(sig)
    @reactive
    def terminate(self):
        self._proc.terminate()
    def wait(self):
        return self.wait_dfr


class ProcessSubsystem(Subsystem):
    NAME = "proc"
    WINDOWS_POLL_INTERVAL = 0.2

    def _init(self):
        self.processes = {}
        self._handler_installed = False

    def _install_child_handler(self):
        if self._handler_installed:
            return
        if hasattr(signal, "SIGCHLD"):
            # POSIX: rely on sigchld
            self.reactor.register_signal(signal.SIGCHLD, self._collect_children)
        else:
            # windows doesn't have sigchld, so let's just poll the process list
            # every so often
            self.reactor.jobs.schedule_every(self.WINDOWS_POLL_INTERVAL, self._windows_poll_children)
        self._handler_installed = True
    
    def _collect_children(self, signum):
        try:
            while True:
                pid, sts = os.waitpid(-1, os.WNOHANG)
                if pid <= 0:
                    break
                proc = self.processes.pop(pid, None)
                if not proc:
                    continue
                # hack: need to call Popen._handle_exitstatus manually
                proc._proc._handle_exitstatus(sts)
                self.reactor.call(proc.on_termination)
        except OSError:
            pass
    
    def _windows_poll_children(self):
        removed = []
        for pid, proc in self.processes.items():
            if not proc.is_alive():
                self.reactor.call(proc.on_termination)
                removed.append(pid)
        for pid in removed:
            self.processes.pop(pid, None)
        if not self.processes:
            self._handler_installed = False
            return False # stop repeating job
    
    @reactive
    def spawn(self, args, cwd = None, env = None, shell = False):
        yield self.reactor.started
        self._install_child_handler()
        p = subprocess.Popen(args, stdin = subprocess.PIPE, stdout = subprocess.PIPE,
            stderr = subprocess.PIPE, cwd = cwd, env = env, shell = shell)
        proc = Process(self.reactor, p, args)
        self.processes[proc.pid] = proc
        rreturn(proc)
    
    @reactive
    def run(self, args, input = None, retcodes = (0,), cwd = None, env = None, 
            shell = False):
        proc = yield self.spawn(args, cwd, env, shell)
        stdout_dfr = ReactorDeferred(self.reactor)
        stderr_dfr = ReactorDeferred(self.reactor)
        
        if input:
            @reactive
            def write_all_stdin():
                yield proc.stdin.write(input)
                yield proc.stdin.close()
            self.reactor.call(write_all_stdin)
        
        @reactive
        def read_all_stdout():
            data = yield proc.stdout.read_all()
            stdout_dfr.set(data)
        self.reactor.call(read_all_stdout)
        
        @reactive
        def read_all_stderr():
            data = yield proc.stderr.read_all()
            stderr_dfr.set(data)
        self.reactor.call(read_all_stderr)
        
        rc = yield proc.wait()
        stdout_data = yield stdout_dfr
        stderr_data = yield stderr_dfr
        
        if retcodes and rc not in retcodes:
            raise ProcessExecutionError("unexpected return code", rc, stdout_data, stderr_data)
        else:
            rreturn((rc, stdout_data, stderr_data))














