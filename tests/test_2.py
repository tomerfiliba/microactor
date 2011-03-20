import microactor
import os


class Application(object):
    @microactor.tasklet
    def main(self):
        raise NotImplementedError()

class StaticHttpApp(Application):
    def __init__(self, reactor, directory):
        Application.__init__(self, reactor)
        self.directory = directory
    
    @microactor.tasklet
    def main(self):
        self.active = True
        listener = yield self.reactor.listen("localhost", 8080)
        while self.active:
            client = yield listener.accept()
            self.reactor.call(self.handle_client, client)
    
    def stop(self):
        self.active = False
    
    @microactor.tasklet
    def handle_client(self, client):
        data = ""
        while True:
            data += yield client.read(16000)
        header, blob = data.find("\r\n\r\n")
        lines = header.splitlines()
        first = lines.pop(0)
        headers = [line.split(":", 1) for line in lines]
        cmd, path, proto = first.split()
        if cmd.lower() == "get":
            microactor.embedded_tasklet(self.handle_client_get(client, path, headers, blob))
        else:
            yield self.client.write("HTTP/1.0 500 Unsupported command\r\n\r\n")
        yield self.client.close()
    
    @microactor.tasklet
    def handle_client_get(self, client, path, headers, blob):
        path2 = os.path.join(self.basepath, path)
        if not os.path.isfile(path2):
            yield client.write("HTTP/1.0 404 Not Found\r\n\r\n")
        else:
            yield client.write("HTTP/1.0 200 OK\r\n\r\n")
            f = yield reactor.file.open(path2, "r")
            while True:
                data = yield f.read(10000)
                yield client.write(data)
            yield f.close()


if __name__ == "__main__":
    with microactor.Reactor() as reactor:
        handler = StaticHttpApp(reactor, ".")
        reactor.call(handler.main)


