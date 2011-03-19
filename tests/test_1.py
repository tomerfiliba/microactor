from microactor import Reactor, monadic


@monadic
def main():
    yield


if __name__ == "__main__":
    Reactor(main)
