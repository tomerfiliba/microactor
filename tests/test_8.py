import microactor


@microactor.reactive
def main(reactor):
    res = yield reactor.dns.resolve("www.google.com")
    print res
    
    proc = yield reactor.proc.spawn(["notepad"])
    print "proc =", proc
    rc = yield proc.wait()
    print "rc =", rc
    yield reactor.stop()



if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

