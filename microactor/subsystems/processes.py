import subprocess
from microactor.subsystems.base import Subsystem
from microactor.utils import Deferred, reactive, rreturn
from microactor.transports import PipeTransport, BufferedTransport
import signal
import os


class Process(object):
    def __init__(self, reactor, proc):
        self.reactor = reactor
        self._proc = proc
        self.stdin = BufferedTransport(PipeTransport(reactor, proc.stdin, "w"))
        self.stdout = BufferedTransport(PipeTransport(reactor, proc.stdout, "r"))
        self.stderr = BufferedTransport(PipeTransport(reactor, proc.stderr, "r"))
        self.pid = proc.pid
        self.waiters_queue = []
    
    def on_termination(self):
        rc = self.returncode
        for dfr in self.waiters_queue:
            dfr.set(rc)
        del self.waiters_queue[:]
    
    @property
    def returncode(self):
        return self._proc.returncode    
    
    def is_alive(self):
        return self._proc.poll() is None
    
    @reactive
    def signal(self, sig):
        self._proc.send_signal(sig)
    
    @reactive
    def terminate(self):
        self._proc.terminate()
    
    def wait(self):
        if not self.is_alive():
            return Deferred(self.returncode)
        dfr = Deferred()
        self.waiters_queue.append(dfr)
        return dfr


class ProcessSubsystem(Subsystem):
    NAME = "proc"
    
    def _init(self):
        self.processes = {}
        if hasattr(signal, "SIGCHLD"):
            self.reactor.register_signal(signal.SIGCHLD, self._collect_children)
        else:
            self.reactor.schedule_repeating(0.2, self._windows_check_children)
    
    def _collect_children(self, signum):
        try:
            while True:
                pid, dummy = os.waitpid(-1, os.WNOHANG)
                if pid <= 0:
                    break
                proc = self.processes.pop(pid, None)
                if not proc:
                    continue
                self.reactor.call(proc.on_termination)
        except OSError:
            pass
    
    def _windows_check_children(self, job):
        removed = []
        for pid, proc in self.processes.items():
            if not proc.is_alive():
                self.reactor.call(proc.on_termination)
                removed.append(pid)
        for pid in removed:
            self.processes.pop(pid, None)
    
    def spawn(self, args, cwd = None, env = None):
        def spawner():
            p = subprocess.Popen(args, stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                stderr = subprocess.PIPE, cwd = cwd, env = env)
            proc = Process(self.reactor, p)
            self.processes[proc.pid] = proc
            dfr.set()
        dfr = Deferred()
        self.reactor.call(spawner)
        return dfr
    
    @reactive
    def run(self, args, input = None, retcodes = (0,), timeout = None, cwd = None, env = None):
        proc = yield self.spawn(args, cwd, env)
        
        stdout_data = [""]
        stderr_data = [""]

        @reactive
        def write_all_stdin():
            yield proc.stdin.write(input)
        if input:
            self.reactor.call(write_all_stdin)
        
        @reactive
        def read_all_stdout():
            stdout_data[0] = yield proc.stdout.read_all()
        self.reactor.call(read_all_stdout)
        
        @reactive
        def read_all_stderr():
            stderr_data[0] = yield proc.stderr.read_all()
        self.reactor.call(read_all_stderr)
        
        rc = yield proc.wait()
        stdout_data = stdout_data[0]
        stderr_data = stderr_data[0]

        if retcodes is not None and rc not in retcodes:
            raise ValueError("process failed", rc, stdout_data, stderr_data)
        else:
            rreturn((rc, stdout_data, stderr_data))














