Microactor: Untwist Your Code
=============================

Microactor (from "micro reactor") is a lightweight, easy-to-use, plug-and-play
reactor framework, designed around the notion of *reactive coroutines*. Unlike
many existing reactors, it attempts to borrow the synchronous programming style
wherever possible, and rely on existing (synchronous) code instead of having
to rewrite everything.

Using Microactor, you no longer need to write lots of factory classes, adhere to
Zope interfaces, be tied to a global reactor, or spread your logic over numerous
callback functions -- you'd do everything just as you would do in synchronous code. 
For example::

    # a very trivial stand-alone echo server
    import microactor
    
    @microactor.reactive
    def main(reactor):
        listener = yield reactor.net.listen_tcp(12345)
        while True:
            conn = yield listener.accept()
            reactor.call(echo_server, conn)
    
    @microactor.reactive
    def echo_server(conn):
        while True:
            data = yield conn.read(1000)
            if data is None:
                break
            yield conn.write(data)
    
    if __name__ == "__main__":
        reactor = microactor.get_reactor()
        reactor.run(main)



