from .colls import MinHeap, Queue

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








