import microactor


class TimeoutError(Exception):
    pass

def timed(timeout, dfr):
    def cancel(job):
        if not dfr.is_set():
            dfr.throw(TimeoutError())
    reactor.schedule(timeout, cancel)
    return dfr

@microactor.reactive
def main(reactor):
    reactor.schedule(5, lambda job: reactor.stop())
    conn = yield reactor.tcp.connect("www.google.com", 80)
    yield conn.write("GET / HTTP/1.1\r\nHost: www.google.com\r\n\r\n")
    data = yield timed(0.1, conn.read(1000))
    print "data = ", repr(data)



if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

