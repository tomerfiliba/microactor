class Task(object):
    def __init__(self, reactor, timestamp, func, args, kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.timestamp = timestamp
    def get_timestamp(self):
        return self.timestamp
    def __cmp__(self, other):
        return cmp(self.get_timestamp(), other.get_timestamp())

class RepeatingTask(object):
    def __init__(self):