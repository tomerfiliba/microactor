def monadic(func):
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        def continuation(res):
            try:
                dfr2 = gen.send(res)
            except StopIteration:
                pass
            else:
                dfr2.callback(continuation)
        continuation(None)
    return wrapper
