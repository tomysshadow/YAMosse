class Once:
  __slots__ = ('_obj', '_count')
  
  def __init__(self, type_=dict):
    # this class is similar to a set
    # but with the distinction we know if an added key already exists
    # with only a single lookup
    self._obj = type_() # the underlying object (anything implementing setdefault)
    self._count = 0 # infinitely increasing count
  
  def __contains__(self, item):
    return item in self._obj
  
  def __len__(self):
    return len(self._obj)
  
  def __iter__(self):
    # for a standard dictionary it would not be necessary to clarify
    # that I want the keys, but for some custom object maybe
    return iter(self.keys())
  
  def clear(self):
    self._obj.clear()
  
  def add(self, key):
    # add the key
    # returns True if key was added, False if existed before
    obj = self._obj
    
    # reset count if obj is empty
    # this must be done here instead of the other methods
    # in case obj changes underneath us
    # (for example, it's a WeakKeyDictionary and a key gets dropped)
    # it's not strictly necessary to reset count
    # particularly in Python, where we can't overflow it anyway
    # but the hope is that it keeps the count in a somewhat reasonable range
    self._count = count = self._count + 1 if obj else 1
    return self._obj.setdefault(key, count) == count
  
  def discard(self, key):
    # discard the key
    # returns True if it existed, False if it did not
    return self._obj.pop(key, 0) != 0
  
  def keys(self):
    return self._obj.keys()