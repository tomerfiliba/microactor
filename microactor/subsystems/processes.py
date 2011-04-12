import os
import signal
import subprocess
from .base import Subsystem
from microactor.utils import Deferred, reactive, rreturn, BufferedTransport


class Process(object):
    def __init__(self, reactor, proc, cmdline):
        self.reactor = reactor
        self.cmdline = cmdline
        self._proc = proc
        self.stdin = BufferedTransport(self.reactor._io.wrap_pipe(proc.stdin, "w"))
        self.stdout = BufferedTransport(self.reactor._io.wrap_pipe(proc.stdout, "r"))
        self.stderr = BufferedTransport(self.reactor._io.wrap_pipe(proc.stderr, "r"))
        self.pid = proc.pid
        self.waiters_queue = []
    
    def __repr__(self):
        return "<Process %r: %r>" % (self.pid, self.cmdline)
    
    def on_termination(self):
        rc = self.returncode
        for dfr in self.waiters_queue:
            self.reactor.call(dfr.set, rc)
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


class ProcessPool(object):
    def __init__(self, reactor, num_of_processes):
        self.reactor = reactor
        self.num_of_processes = num_of_processes
    
    def call(self, funcname, *args, **kwargs):
        pass


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
    
    def spawn(self, args, cwd = None, env = None):
        def spawner():
            try:
                p = subprocess.Popen(args, stdin = subprocess.PIPE, stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE, cwd = cwd, env = env)
            except Exception as ex:
                self.reactor.call(dfr.throw, ex)
            else:
                proc = Process(self.reactor, p, args)
                self.processes[proc.pid] = proc
                self.reactor.call(dfr.set, proc)
        self._install_child_handler()
        dfr = Deferred()
        self.reactor.call(spawner)
        return dfr
    
    @reactive
    def run(self, args, input = None, retcodes = (0,), cwd = None, env = None):
        proc = yield self.spawn(args, cwd, env)
        stdout_dfr = Deferred()
        stderr_dfr = Deferred()

        @reactive
        def write_all_stdin():
            yield proc.stdin.write(input)
            yield proc.stdin.flush()
        if input:
            self.reactor.call(write_all_stdin)
        
        @reactive
        def read_all_stdout():
            data = yield proc.stdout.read_all()
            self.reactor.call(stdout_dfr.set, data)
        self.reactor.call(read_all_stdout)
        
        @reactive
        def read_all_stderr():
            data = yield proc.stderr.read_all()
            self.reactor.call(stderr_dfr.set, data)
        self.reactor.call(read_all_stderr)
        
        rc = yield proc.wait()
        stdout_data = yield stdout_dfr
        stderr_data = yield stderr_dfr

        if retcodes and rc not in retcodes:
            raise ValueError("process failed", rc, stdout_data, stderr_data)
        else:
            rreturn((rc, stdout_data, stderr_data))
    
    def process_pool(self, service, max_processes):
        pass



