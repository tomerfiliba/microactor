Windows
=======
* Consoles
  * Resort to a thread blocking on WaitForMultipleObjects on console input
* Files, pipes: finish implementation

POSIX
=====
* attempt a per-platform FIONREAD/TIOCOUTQ ioctls() to determined available 
  read and write sizes
* tty abstraction (rely on http://github.com/tomerfiliba/conso)

Subsystems
==========
* SSH tunneling, remote execution
* Process pool
* Files, pipes subsystem
* Console abstraction (like curses)
* Network:
  * TCP server abstraction
* Spawn reactor thread (e.g. server)

Protocols
=========
* HTTP
* FTP
* SMTP
* Reactive RPC

Services
========
* HTTP server


Future
======
* Web GUI:
  * A lightweight HTTP server with some client-side js libs, using html5 rendering,
    would make a great GUI library, instead of having to integrate with desktop
    UI mainloops
* Desktop GUI integration?
  * qt
  * gtk
  * wxpython
* Protocols:
  * reactive DNS?
  * reactive SSH?
    * paramiko integration?








