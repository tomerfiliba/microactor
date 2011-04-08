To do
=====
* Better exception tracebacks
* logging!
* basic RPC
* Debug mode?
* block signals on worker threads
* generic server 
* negotiation

* reactive:

  * require reactor argument?
  * Check for forgetting to yield a deferred in a reactive function?
  * parallel?
  * timeout

sigprocmask:
buf=ctypes.create_string_buffer(32)
libc.sigfillset(buf)
libc.sigprocmask(0, buf, 0) # SIG_BLOCK = 0

import os
import signal
os.kill(os.getpid(), signal.SIGINT) # nothing happens

