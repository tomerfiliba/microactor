import os
import signal
import subprocess
from .base import Subsystem
from microactor.utils import ReactorDeferred, reactive, rreturn
from microactor.utils import BufferedTransport, safe_import
from microactor.protocols.remoting import RemotingClient
from microactor.utils.transports import DuplexStreamTransport
win32iocp = safe_import("microactor.arch.windows.iocp")
msvcrt = safe_import("msvcrt")


if win32iocp:
    # praise monkey patching, for it pwnz
    # we want the pipes to have FILE_FLAG_OVERLAPPED, that's all 
    import _subprocess
    _subprocess.CreatePipe = lambda a, b: win32iocp.create_overlapped_pipe()


class ProcessExecutionError(Exception):
    def __init__(self, msg, rc, stdout, stderr):
        Exception.__init__(self, msg, rc, stdout, stderr)
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr
    
    @classmethod
    @reactive
    def from_proc(cls, msg, proc):
        stdout = yield proc.stdout.read_all()
        stderr = yield proc.stderr.read_all()
        rreturn (cls(msg, proc.returncode, stdout, stderr))

class WorkerProcessTerminated(ProcessExecutionError):
    pass

class Process(object):
    def __init__(self, reactor, proc, cmdline):
        self.reactor = reactor
        self.cmdline = cmdline
        self._proc = proc
        self.stdin = BufferedTransport(self.reactor.io._wrap_pipe(proc.stdin, "w"))
        self.stdout = BufferedTransport(self.reactor.io._wrap_pipe(proc.stdout, "r"))
        self.stderr = BufferedTransport(self.reactor.io._wrap_pipe(proc.stderr, "r"))
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


class PooledProcess(object):
    def __init__(self, proc):
        self.proc = proc
        self.reactor = proc.reactor
        self.client = RemotingClient(DuplexStreamTransport(self.proc.stdout, self.proc.stdin))
        self.queue = set()
    
    @reactive
    def close(self):
        self.queue.clear()
        self.client.close()  # will close the proc's stdin and stdout
        if not win32iocp:
            # can't send SIGINT on windows... let's hope the process will 
            # notice that it's stdin has been closed
            self.proc.signal(signal.SIGINT)
        yield self.reactor.jobs.sleep(0.3)
        if self.proc.is_alive():
            self.proc.terminate()
    
    def queue_size(self):
        return len(self.queue)
    
    @reactive
    def _wait_termination(self):
        yield self.proc.wait()
        for dfr in self.queue:
            if not dfr.is_set():
                exc = yield WorkerProcessTerminated.from_proc(
                    "worker process has terminated with pending requests", self.proc)
                dfr.throw(exc) 

    @reactive
    def enqueue(self, func, args, kwargs):
        dfr = yield self.client._call(func, args, kwargs)
        dfr.register(lambda isexc, obj: self.queue.discard(dfr))
        self.queue.add(dfr)
        rreturn(dfr)
    
class ProcessPool(object):
    def __init__(self, reactor, process_factory, max_processes):
        self.reactor = reactor
        self.process_factory = process_factory
        self.processes = set()
        self.max_processes = max_processes

    @reactive
    def close(self):
        dfrlist = [proc.close() for proc in self.processes]
        for dfr in dfrlist:
            yield dfr

    @reactive
    def _collector(self, proc):
        yield proc._wait_termination()
        self.processes.discard(proc)
    
    @reactive
    def _get_process(self):
        # find an empty worker
        minimal_proc = None
        for proc in self.processes:
            if not proc.queue:
                rreturn(proc)
            if minimal_proc is None or minimal_proc.queue_size() > proc.queue_size():
                minimal_proc = proc
        
        # otherwise, see if we can spawn a new worker
        if len(self.processes) < self.max_processes:
            proc = yield self.process_factory()
            proc2 = PooledProcess(proc)
            self.processes.add(proc2)
            self.reactor.call(self._collector, proc2)
            rreturn(proc2)
        
        # no, just return the minimal woker
        rreturn(minimal_proc)
    
    @reactive
    def _call(self, func, args, kwargs):
        proc = yield self._get_process()
        dfr = yield proc.enqueue(func, args, kwargs)
        rreturn(dfr)

    @reactive
    def call(self, func, *args, **kwargs):
        dfr = yield self._call(func, args, kwargs)
        res = yield dfr
        rreturn(res)


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

        if input:
            @reactive
            def write_all_stdin():
                yield proc.stdin.write(input)
                yield proc.stdin.close()
            self.reactor.call(write_all_stdin)
        else:
            yield proc.stdin.close()

        stdout_dfr = proc.stdout.read_all()
        stderr_dfr = proc.stderr.read_all()
        rc = yield proc.wait()
        stdout_data = yield stdout_dfr
        stderr_data = yield stderr_dfr

        if retcodes and rc not in retcodes:
            raise ProcessExecutionError("unexpected return code", rc, stdout_data, stderr_data)
        else:
            rreturn((rc, stdout_data, stderr_data))
    
    def create_pool(self, args, max_processes, cwd = None, env = None, shell = False):
        factory = lambda: self.spawn(args, cwd, env, shell)
        return ProcessPool(self.reactor, factory, max_processes)





