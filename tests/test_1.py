import microactor


@microactor.tasklet
def echo_server(reactor):
    listener = yield reactor.tcp.listen("localhost", 12233)
    while True:
        client = yield listener.on_accept()
        reactor.call(echo_handler, client)

@microactor.tasklet
def echo_handler(client):
    while True:
        blob = yield client.read(1000)
        yield client.write(blob)


if __name__ == "__main__":
    microactor.main(echo_server)


