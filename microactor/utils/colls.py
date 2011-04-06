import heapq
import threading
from .deferred import Deferred


class Queue(object):
    """amortized O(1) queue (at least I think so :)"""
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

class Blocker(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._waiters = []
        self._unattented_wakeups = 0
    def clear(self):
        with self._lock:
            self._unattented_wakeups = 0
    def wakeup(self):
        with self._lock:
            if self._waiters:
                w = self._waiters.pop(0)
            else:
                w = None
                self._unattented_wakeups += 1
        if w:
            w.release()
    def wait(self):
        w = threading.Lock()
        w.acquire()
        with self._lock:
            if self._unattented_wakeups > 0:
                self._unattented_wakeups -= 1
                w.release()
            else:
                self._waiters.append(w)
        with w:
            pass

class SynchronizedQueue(object):
    def __init__(self):
        self._lock = threading.Lock()
        self._queue = Queue()
    def __len__(self):
        return len(self._queue)
    def push(self, obj):
        with self._lock:
            self._queue.push(obj)
    def pop(self):
        with self._lock:
            return self._queue.pop()
    def clear(self):
        with self._lock:
            self._queue.clear()

class ThreadSafeQueue(object):
    """a thread-safe queue (uses locking)"""
    def __init__(self):
        self._non_empty = Blocker()
        self._queue = SynchronizedQueue()
        self._lock = threading.Lock()
    def __len__(self):
        return len(self._queue)
    def push(self, obj):
        with self._lock:
            self._queue.push(obj)
            self._non_empty.wakeup()
    def pop(self):
        while True:
            self._non_empty.wait()
            if self._queue:
                return self._queue.pop()
    def clear(self):
        with self._lock:
            self._queue.clear()
            self._non_empty.clear()

class ReactiveQueue(object):
    """a reactive queue"""
    def __init__(self):
        self.data_queue = Queue()
        self.waiters_queue = Queue()
    def __len__(self):
        return len(self.data_queue) + len(self.waiters_queue)
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
        if self.queue:
            dfr.set(self.data_queue.pop())
        else:
            self.waiters_queue.push(dfr)
        return dfr




if __name__ == "__main__":
    import time

    q = ThreadSafeQueue()
    q.push(500)
    
    def f(name):
        for i in range(5):
            print "%s waiting\n" % (name,),
            x = q.pop()
            print "%s got %r\n" % (name, x),
    threading.Thread(target = f, args=("T1",)).start()
    threading.Thread(target = f, args=("T2",)).start()
    threading.Thread(target = f, args=("T3",)).start()

    q.push(501)
    q.push(502)
    q.push(503)
    q.push(504)   
    q.push(505)
    time.sleep(2)
    q.push(506)
    q.push(507)
    time.sleep(2)
    q.push(508)
    q.push(509)
    q.push(510)
    q.push(511)
    q.push(512)
    q.push(513)
    q.push(514)

















