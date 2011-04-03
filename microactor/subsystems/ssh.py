from microactor.subsystems.base import Subsystem
from microactor.utils import reactive, rreturn


# modified from the stdlib ``pipes`` module
def shquote(text):
    _safechars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@%_-+=:,./'
    _funnychars = '"`$\\'
    
    if not text:
        return "''"
    for c in text:
        if c not in _safechars:
            break
    else:
        return text
    if "'" not in text:
        return "'" + text + "'"
    res = "".join(('\\' + c if c in _funnychars else c) for c in text)
    return '"' + res + '"'


class SshTunnel(object):
    WAITER_CMDLINE = ["python", "-u", "-c", 
        r"""import sys;sys.stdout.write("ready\n\n\n");sys.stdout.flush();sys.stdin.readline()"""]
    
    def __init__(self, sshctx, loc_host, loc_port, rem_host, rem_port):
        self.sshctx = sshctx
        self.loc_host = loc_host
        self.loc_port = loc_port
        self.rem_host = rem_host
        self.rem_port = rem_port
        self.proc = None
    
    @reactive
    def start(self):
        if self.proc is not None:
            raise ValueError("tunnel already active")
        proc = yield self.ssh.spawn(self.WAITER_CMDLINE, options = {
            "L" : "%s/%s/%s/%s" % (self.loc_host, self.loc_port, self.rem_host, self.rem_port)
        })
        banner = proc.stdout.read_line().strip()
        if banner != "ready":
            proc.kill()
            raise ValueError("tunnel failed")
        self.proc = proc
    
    @reactive
    def close(self):
        if not self.proc:
            return
        yield self.proc.stdin.write("foo\r\n\r\n\r\n")
        yield self.proc.stdin.flush()
        yield self.proc.wait()
        self.proc = None
    
    @reactive
    def connect(self):
        conn = yield self.sshctx.reactor.tcp.connect(self.loc_host, self.loc_port)
        rreturn(conn)


class SshContext(object):
    def __init__(self, reactor, host, username = None, keyfile = None, 
            port = None, force_tty = False, 
            ssh_binary = "ssh", ssh_env = None, ssh_cwd = None, 
            scp_binary = "scp", scp_env = None, scp_cwd = None):
        self.reactor = reactor
        self.host = host
        self.username = username
        self.keyfile = keyfile
        self.port = port
        self.force_tty = force_tty
        self.ssh_binary = ssh_binary
        self.ssh_env = ssh_env
        self.ssh_cwd = ssh_cwd
        self.scp_binary = scp_binary
        self.scp_env = scp_env
        self.scp_cwd = scp_cwd
    
    def __str__(self):
        port = ":%s" % (self.port,) if self.port else ""
        user = "%s@" % (self.username,) if self.username else ""
        return "ssh://%s%s%s" % (user, self.host, port)

    def _convert_kwargs_to_args(self, kwargs):
        args = []
        for k, v in kwargs.iteritems():
            if v is True:
                args.append("-%s" % (k,))
            elif v is False:
                pass
            else:
                args.append("-%s" % (k,))
                args.append(str(v))
        return args

    def _process_scp_cmdline(self, kwargs):
        if kwargs is None:
            kwargs = {}
        args = [self.scp_binary]
        if self.keyfile and "i" not in kwargs:
            kwargs["i"] = self.keyfile
        if self.port and "P" not in kwargs:
            kwargs["P"] = self.port
        args.extend(self._convert_kwargs_to_args(kwargs))
        host = "%s@%s" % (self.user, self.host) if self.user else self.host
        return args, host
    
    def _process_ssh_cmdline(self, kwargs):
        if kwargs is None:
            kwargs = {}
        args = [self.ssh_binary]
        if self.keyfile and "i" not in kwargs:
            kwargs["i"] = self.keyfile
        if self.port and "p" not in kwargs:
            kwargs["p"] = self.port
        args.extend(self._convert_kwargs_to_args(kwargs))
        args.append("%s@%s" % (self.user, self.host) if self.user else self.host)
        return args

    @reactive
    def spawn(self, args, options = None):
        cmdline = self._process_ssh_cmdline(options)
        cmdline.extend(shquote(a) for a in args)
        proc = yield self.reactor.proc.spawn(cmdline, cwd = self.ssh_cwd, 
            env = self.ssh_env)
        rreturn(proc)
    
    @reactive
    def run(self, args, input = None, retcodes = (0,), options = None):
        cmdline = self._process_ssh_cmdline(options)
        cmdline.extend(shquote(a) for a in args)
        res = yield self.reactor.proc.run(cmdline, input = input, 
            retcodes = retcodes, cwd = self.ssh_cwd, env = self.ssh_env)
        rreturn(res)
    
    @reactive
    def upload(self, src, dst, recursive = True, options = None):
        if options is None:
            options = {}
        if recursive:
            options["r"] = True
        cmdline, host = self._process_scp_cmdline(options)
        cmdline.append(src)
        cmdline.append("%s:%s" % (host, dst))
        res = yield self.reactor.proc.run(cmdline, cwd = self.ssh_cwd, 
            env = self.ssh_env)
        rreturn(res)
    
    @reactive
    def download(self, src, dst, recursive = True, options = None):
        if options is None:
            options = {}
        if recursive:
            options["r"] = True
        cmdline, host = self._process_scp_cmdline(options)
        cmdline.append("%s:%s" % (host, dst))
        cmdline.append(src)
        res = yield self.reactor.proc.run(cmdline, cwd = self.ssh_cwd, 
            env = self.ssh_env)
        rreturn(res)
    
    @reactive
    def tunnel(self, loc_port, rem_port, loc_host = "localhost", rem_host = "localhost"):
        tun = SshTunnel(self, loc_host, loc_port, rem_host, rem_port)
        yield tun.start()
        rreturn(tun)


class SshSubsystem(Subsystem):
    NAME = "ssh"
    
    def __call__(self, *args, **kwargs):
        return SshContext(self.reactor, *args, **kwargs)













