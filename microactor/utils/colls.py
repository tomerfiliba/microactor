import heapq
from .deferred import Deferred


class Queue(object):
    """amortized O(1) queue (or am i wrong?)"""
    __slots__ = ["_rindex", "_items"]
    def __init__(self):
        self._rindex = 0
        self._items = []
    def __len__(self):
        return len(self._items) - self._rindex
    def _compact(self):
        if len(self._items) / self._rindex < 2:
            return
        del self._items[:self._rindex]
        self._rindex = 0
    def push(self, obj):
        self._items.append(obj)
    def peek(self):
        return self._items[self._rindex]
    def pop(self):
        obj = self._items[self._rindex]
        self._rindex += 1
        self._compact()
        return obj
    def clear(self):
        del self._items[:]
        self._rindex = 0

class MinHeap(object):
    """a wrapper for the heapq module"""
    __slots__ = ["_items"]
    def __init__(self, seq = ()):
        self._items = list(seq)
        heapq.heapify(self._items)
    def push(self, obj):
        heapq.heappush(self._items, obj)
    def pop(self):
        return heapq.heappop(self._items)
    def peek(self):
        return self._items[0]
    def __len__(self):
        return len(self._items)

class ReactiveQueue(object):
    """a reactive queue"""
    __slots__ = ["data_queue", "waiters_queue"]
    def __init__(self):
        self.data_queue = Queue()
        self.waiters_queue = Queue()
    def __len__(self):
        return len(self.data_queue)
    def push(self, obj):
        """pushes an item into the queue"""
        if self.waiters_queue:
            dfr = self.waiters_queue.pop()
            dfr.set(obj)
        else:
            self.data_queue.push(obj)
    def pop(self):
        """returns a Deferred that will hold the popped item, when one is 
        available"""
        dfr = Deferred()
        if self.data_queue:
            dfr.set(self.data_queue.pop())
        else:
            self.waiters_queue.push(dfr)
        return dfr


class Mutex(object):
    __slots__ = ["owned", "waiters"]
    def __init__(self):
        self.owned = False
        self.waiters = Queue()
    def acquire(self):
        dfr = Deferred()
        if not self.owned:
            self.owned = True
            dfr.set()
        else:
            self.waiters.push(dfr)
        return dfr
    def release(self):
        if not self.waiters:
            if not self.owned:
                raise ValueError("mutex released too many timed")
            self.owned = False
        else:
            dfr = self.waiters.pop()
            dfr.set()




