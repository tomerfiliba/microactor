import heapq
import threading


class Queue(object):
    """
    amortized O(1) queue ?
    """
    def __init__(self):
        self._rindex = 0
        self._items = []
    def _compact(self):
        if len(self._items) / self._rindex < 2:
            return
        self._items = self._items[self._rindex:]
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
    def __len__(self):
        return len(self._items) - self._rindex

class MinHeap(object):
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

class ThreadSafeQueue(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.queue = Queue()
    def push(self, obj):
        with self.lock:
            self.queue.push(obj)
    def pop(self):
        with self.lock:
            return self.queue.pop()
    def __len__(self):
        return len(self.queue)

class ReactiveQueue(object):
    def __init__(self):
        self.data_queue = Queue()
        self.waiters_queue = Queue()
    
    def push(self, obj):
        if self.waiters_queue:
            dfr = self.waiters_queue.pop()
            dfr.set(obj)
        else:
            self.data_queue.push(obj)
    
    def pop(self):
        from microactor.utils import Deferred
        dfr = Deferred()
        if self.queue:
            dfr.set(self.data_queue.pop())
        else:
            self.waiters_queue.push(dfr)
        return dfr
    
    def __len__(self):
        return len(self.data_queue)





