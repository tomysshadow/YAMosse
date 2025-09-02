import unittest
from weakref import WeakKeyDictionary

import yamosse.once as once

class Weak: pass


class TestOnce(unittest.TestCase):
  def test_once(self):
    o = once.Once()
    
    self.assertTrue(o.add('first'))
    self.assertFalse(o.add('first'))
    
    self.assertTrue(o.add('second'))
    self.assertFalse(o.add('second'))
    
    self.assertFalse(o.add('first'))
    
    self.assertTrue(o.add('third'))
    self.assertFalse(o.add('third'))
    
    self.assertFalse(o.add('second'))
  
  def test_once_len(self):
    o = once.Once()
    
    o.add('first')
    self.assertEqual(len(o), 1)
    
    o.add('second')
    self.assertEqual(len(o), 2)
    
    o.add('first')
    o.add('third')
    self.assertEqual(len(o), 3)
    
    o.clear()
    self.assertEqual(len(o), 0)
  
  def test_once_in(self):
    o = once.Once()
    
    o.add('first')
    self.assertIn('first', o)
    
    o.add('second')
    self.assertIn('first', o)
    self.assertIn('second', o)
    
    o.add('first')
    o.add('third')
    self.assertIn('first', o)
    self.assertIn('second', o)
    self.assertIn('third', o)
    
    o.clear()
    self.assertNotIn('first', o)
    self.assertNotIn('second', o)
    self.assertNotIn('third', o)
  
  def test_once_iter(self):
    o = once.Once()
    
    o.add('first')
    o.add('second')
    o.add('third')
    
    o.discard('second')
    
    keys = ('first', 'third')
    
    for expected, key in zip(keys, o):
      self.assertEqual(expected, key)
    
    i = iter(o)
    self.assertEqual('first', next(i))
    self.assertEqual('third', next(i))
    
    self.assertEqual(o.keys(), dict.fromkeys(keys).keys())
  
  def test_once_weak(self):
    o = once.Once(type_=WeakKeyDictionary)
    
    weak = Weak()
    
    self.assertTrue(o.add(weak))
    self.assertFalse(o.add(weak))
    
    weak = None
    
    self.assertEqual(len(o), 0)
    
    weak = Weak()
    
    self.assertTrue(o.add(weak))
    self.assertFalse(o.add(weak))
    
    self.assertEqual(len(o), 1)


if __name__ == '__main__': unittest.main()