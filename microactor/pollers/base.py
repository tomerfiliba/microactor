class BasePoller(object):
    def close(self):
        pass
    @classmethod
    def supported(cls):
        return False
    
    def register_read(self, fileobj):
        raise NotImplementedError()
    def register_write(self, fileobj):
        raise NotImplementedError()
    def unregister_read(self, fileobj):
        raise NotImplementedError()
    def unregister_write(self, fileobj):
        raise NotImplementedError()
    
    def poll(self, timeout):
        raise NotImplementedError()


class FakePoller(BasePoller):
    @classmethod
    def supported(cls):
        return True