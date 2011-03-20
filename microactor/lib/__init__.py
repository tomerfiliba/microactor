import heapq

class MinHeap(object):
    def __init__(self, seq = ()):
        self._seq = list(seq)
        heapq.heapify(self._seq)
    def __repr__(self):
        return "Heap(%r)" % (self._seq)
    def __len__(self):
        return len(self._seq)
    def __bool__(self):
        return bool(self._seq)
    __nonzero__ = __bool__
    def empty(self):
        return not self
    def peek_min(self):
        return self._seq[0]
    def pop_min(self): 
        return heapq.heappop(self._seq)
    def push(self, obj):
        heapq.heappush(self._seq, obj)


