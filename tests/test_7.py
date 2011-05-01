import microactor
from microactor.subsystems.net import BaseSocketHandler
from microactor.utils import BufferedTransport


class EchoHandler(BaseSocketHandler):
    @microactor.reactive
    def start(self):
        conn = BufferedTransport(self.conn)
        while True:
            line = yield conn.read_line()
            if line is None:
                break
            yield conn.write(line)
            yield conn.flush()

@microactor.reactive
def main(reactor):
    reactor.jobs.schedule(2, reactor.stop)
    server = yield reactor.net.serve(EchoHandler, 12345)
    client = yield reactor.net.connect_tcp("localhost", 12345)
    client = BufferedTransport(client)
    for line in ["hello world\n", "foo bar\n", "spam bacon and eggs\n"]:
        yield client.write(line)
        yield client.flush()
        line2 = yield client.read_line()
        print repr(line)
        print repr(line2)
        print
    
    server.close() # causes ERROR_NETNAME_DELETED in GetQueuedCompletionStatus
    

if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)

