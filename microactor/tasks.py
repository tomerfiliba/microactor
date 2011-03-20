class BaseTask(object):
    def __init__(self, callback, timestamp):
        self._callback = callback
        self._timestamp = timestamp

    def get_timestamp(self):
        raise NotImplementedError()

class SingleTask(object):
    def __init__(self, callback, timestamp):
        self._callback = callback
        self._timestamp = timestamp
        self._active = True
        self._skip_overdue = False
    def get_timestamp(self):
        return self._timestamp()
    def __cmp__(self, other):
        return cmp(self.get_timestamp(), other.get_timestamp())
    def cancel(self):
        self._active = False
    def _invoke(self):
        if 




