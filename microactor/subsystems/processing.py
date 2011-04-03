import os
import signal
import subprocess
import threading
from microactor.subsystems.base import Subsystem
from microactor.utils import Deferred, reactive, rreturn
from microactor.transports import PipeTransport, BufferedTransport
from microactor.lib.colls import ThreadSafeQueue


class Process(object):
    def __init__(self, reactor, proc, cmdline):
        self.reactor = reactor
        self.cmdline = cmdline
        self._proc = proc
        self.stdin = BufferedTransport(PipeTransport(reactor, proc.stdin, "w"))
        self.stdout = BufferedTransport(PipeTransport(reactor, proc.stdout, "r"))
        self.stderr = BufferedTransport(PipeTransport(reactor, proc.stderr, "r"))
        self.pid = proc.pid
        self.waiters_queue = []
    
    def __repr__(self):
        return "<Process %r: %r>" % (self.pid, self.cmdline)
    
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


class ProcessPool(object):
    def __init__(self, reactor, num_of_processes):
        self.reactor = reactor
        self.num_of_processes = num_of_processes
    
    def call(self, funcname, *args, **kwargs):
        pass


class ProcessSubsystem(Subsystem):
    NAME = "proc"
    DEPENDS = ["jobs"]
    POLL_INTERVAL = 0.2
    
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
            self.reactor.jobs.schedule_every(self.POLL_INTERVAL, self._windows_check_children)
        self._handler_installed = True
    
    def _collect_children(self, signum):
        try:
            while True:
                pid, _ = os.waitpid(-1, os.WNOHANG)
                if pid <= 0:
                    break
                proc = self.processes.pop(pid, None)
                if not proc:
                    continue
                self.reactor.call(proc.on_termination)
        except OSError:
            pass
    
    def _windows_check_children(self):
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
                dfr.throw(ex)
            else:
                proc = Process(self.reactor, p, args)
                self.processes[proc.pid] = proc
                dfr.set(proc)
        self._install_child_handler()
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



class ThreadPool(object):
    def __init__(self, reactor, num_of_threads):
        self.reactor = reactor
        self.queues = []
        self.active = True
        self.running_threads = ThreadSafeQueue()
        for i in range(num_of_threads):
            queue = ThreadSafeQueue()
            thd = threading.Thread(name = "pool-%r" % (i,), target = self._thread_pool_main)
            self.running_threads.put(thd)
            self.worker_queues.append(queue)
            thd.start()
    
    def close(self):
        self.active = False
        for queue in self.queues:
            queue.put((None, None, None, None))
        return self.reactor.threading.call(self.running_threads.join)
    
    def _thread_pool_main(self, queue):
        try:
            while self.active:
                func, args, kwargs, dfr = queue.get()
                if not self.active:
                    dfr.cancel()
                    break
                try:
                    res = func(*args, **kwargs)
                except Exception as ex:
                    dfr.throw(ex)
                else:
                    dfr.set(res)
        finally:
            self.running_threads.task_done()
    
    def _choose_next_queue(self):
        # we're using the *non-thread-safe* _qsize() as the key. this is done
        # for performance reasons, as we only need a heuristic of where to 
        # enqueue the next task. the worst thing is, the chosen queue's actual
        # size will decrease, which is good for us anyway.  
        return min((queue for _, queue in self.threads), key = ThreadSafeQueue._qsize)
    
    def call(self, func, *args, **kwargs):
        dfr = Deferred()
        queue = self._choose_next_queue()
        queue.push((func, args, kwargs, dfr))
        return dfr


class ThreadingSubsystem(Subsystem):
    NAME = "threading"
    
    def _init(self):
        self.threads = set()
    
    def call(self, func, *args, **kwargs):
        dfr = Deferred()
        def wrapper():
            try:
                res = func(*args, **kwargs)
            except Exception as ex:
                dfr.throw(ex)
            else:
                dfr.set(res)
            finally:
                self.threads.discard(thd)
        thd = threading.Thread(target = wrapper)
        self.threads.add(thd)
        thd.start()
        return dfr
    
    def thread_pool(self, size):
        return ThreadPool(self.reactor, size)








