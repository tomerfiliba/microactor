import time
import heapq


def clock():
    return time.time()

def singleton(cls):
    return cls()

class Queue(object):
    def __init__(self):
        self._rindex = 0
        self._items = []
    def _compact(self):
        if len(self._items) / self._rindex > 2:
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





