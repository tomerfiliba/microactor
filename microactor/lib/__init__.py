import heapq



class Queue(object):
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

class istr(str):
    def __new__(cls, obj):
        if isinstance(obj, istr):
            return obj
        s = str.__new__(cls, obj)
        s._lower = str.lower(s)
        s._hash = hash(s._lower)
        return s
    def lower(self):
        return self._lower
    def __hash__(self):
        return self._hash
    def __eq__(self, other):
        return self._lower == other.lower()
    def __ne__(self, other):
        return self._lower != other.lower()
    def __gt__(self, other):
        return self._lower > other.lower()
    def __ge__(self, other):
        return self._lower >= other.lower()
    def __lt__(self, other):
        return self._lower < other.lower()
    def __le__(self, other):
        return self._lower <= other.lower()








