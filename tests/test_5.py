import microactor


@microactor.reactive
def main(reactor):
    try:
        #res = yield reactor.proc.run("notepad")
        res = yield reactor.proc.run("dir", shell=True)
        print res
    finally:
        reactor.stop()


if __name__ == "__main__":
    reactor = microactor.get_reactor()
    reactor.run(main)


