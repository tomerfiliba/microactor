Microactor: Untwisting your Code 
================================

Microactor (a portmanteau of "micro reactor") is a minimalistic, lightweight,
`coroutine-based <http://en.wikipedia.org/wiki/Coroutine>`_ asynchronous framework 
for Python. Unlike many such frameworks, it is designed as a "plug-in reactor":
you can create multiple reactors (one per thread, or even fire up one inside a 
blocking function), and it's deisgned to play along nicely with existing 
(synchronous) code.

It takes the coroutines-approach for asynchronicity, unlike the `inverse flow of
control <http://en.wikipedia.org/wiki/Inversion_of_control>`_ that is employed by
frameworks such as Twisted. The benefits of this approach are numerous:

* Business logic is not spread over many places

* Simpler, in-code state machines ("code flow is the state machine")

* More compact code: No need for callbacks, factory classes, or multiple 
  inheritance schemes
  
* Easier to design (no inversion of control)

* Better exception tracebacks and easier debugging (more "synchronous" mode of thinking)

* More composable code: it's easy to take wrap a "low-level" coroutine with
  a "higher-level" one. 

For instance::

    import microactor
    
    @microactor.reactive
    def my_func(reactor):
        listener = yield reactor.tcp.listen(12345)
        client = yield listener.accept()
        data = yield client.read(11)
        if data == "hello world":
            yield client.write("hello to you too")
        else:
            yield client.write("you need to say hello first!")
        yield client.close()
    
    if __name__ == "__main__":
        reactor = microactor.get_reactor()
        reactor.run(my_func)












