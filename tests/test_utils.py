import unittest

import yamosse.utils as utils

class TestUtils(unittest.TestCase):
  def test_try_int_integer(self):
    self.assertIsInstance(utils.try_int('10'), int)
  
  def test_try_int_string(self):
    self.assertIsInstance(utils.try_int('abcde'), str)
  
  def test_try_int_base(self):
    self.assertIsInstance(utils.try_int('0x10', base=16), int)
  
  def test_try_split_string(self):
    self.assertEqual(len(utils.try_split('tree headings')), 2)
  
  def test_try_split_delimiter(self):
    self.assertEqual(len(utils.try_split('tree,headings', ',')), 2)
  
  def test_try_split_sequence(self):
    self.assertEqual(len(utils.try_split(('tree', 'headings'))), 2)
  
  def test_ascii_backslashreplace_unicode(self):
    self.assertEqual(utils.ascii_backslashreplace('I \u2665 YAMosse'), r'I \u2665 YAMosse')
  
  def test_ascii_backslashreplace_cyrillic(self):
    self.assertEqual(
      utils.ascii_backslashreplace('\u041a\u0438\u0440\u0438\u043b\u0438\u0446\u0430'),
      r'\u041a\u0438\u0440\u0438\u043b\u0438\u0446\u0430'
    )
  
  def test_ascii_backslashreplace_latin1(self):
    self.assertEqual(utils.ascii_backslashreplace('\xfc'), r'\xfc')
  
  def test_latin1_unescape(self):
    self.assertEqual(utils.latin1_unescape(r'Newline \n Tab \t End'), 'Newline \n Tab \t End')
  
  def test_latin1_unescape_unicode(self):
    self.assertEqual(utils.latin1_unescape('I \u2665 YAMosse'), 'I \u2665 YAMosse')
  
  def test_latin1_unescape_cyrillic(self):
    self.assertEqual(
      utils.latin1_unescape('\u041a\u0438\u0440\u0438\u043b\u0438\u0446\u0430'),
      '\u041a\u0438\u0440\u0438\u043b\u0438\u0446\u0430'
    )
  
  def test_latin1_unescape_latin1(self):
    self.assertEqual(utils.latin1_unescape('\xfc'), '\xfc')
  
  def test_clamp_within(self):
    self.assertEqual(utils.clamp(5, -20, 20), 5)
  
  def test_clamp_above(self):
    self.assertEqual(utils.clamp(22, -20, 20), 20)
  
  def test_clamp_below(self):
    self.assertEqual(utils.clamp(-22, -20, 20), -20)
  
  def test_hours_minutes(self):
    self.assertEqual(utils.hours_minutes(90), '1:30')
  
  def test_hours_minutes_float(self):
    self.assertEqual(utils.hours_minutes(90.2), '1:30')
  
  def test_hours_minutes_rollover(self):
    self.assertNotEqual(utils.hours_minutes(59.9), '0:60')
  
  def test_hours_minutes_h(self):
    self.assertEqual(utils.hours_minutes(60 * 60), '1:00:00')
  
  def test_hours_minutes_nodays(self):
    self.assertEqual(utils.hours_minutes(60 * 60 * 24 * 3), '72:00:00')
  
  def test_intersects(self):
    self.assertTrue(utils.intersects(['a', 'b', 'c'], ['b', 'c', 'd']))
  
  def test_intersects_not(self):
    self.assertFalse(utils.intersects(['a', 'b', 'c'], ['d', 'e', 'f']))
  
  def test_str_ensureprefix(self):
    self.assertEqual(utils.str_ensureprefix('abc', '.'), '.abc')
  
  def test_str_ensureprefix_single(self):
    self.assertEqual(utils.str_ensureprefix('.abc', '.'), '.abc')
  
  def test_str_ensureprefix_multiple(self):
    self.assertEqual(utils.str_ensureprefix('..abc', '.'), '..abc')
  
  def test_dict_peekitem(self):
    d = {}
    d[0] = 'a'
    d[2] = 'c'
    d[1] = 'b'
    
    key, value = utils.dict_peekitem(d)
    self.assertEqual(key, 1)
    self.assertEqual(value, 'b')
  
  def _dict_unsorted(self):
    d = {}
    d[2] = 'a'
    d[1] = 'b'
    d[0] = 'c'
    return d
  
  def test_dict_sorted(self):
    d = self._dict_unsorted()
    
    d = utils.dict_sorted(d)
    
    for index, key in enumerate(d.keys()):
      self.assertEqual(key, index)
    
    for index, value in zip(('c', 'b', 'a'), d.values(), strict=True):
      self.assertEqual(index, value)
  
  def test_dict_sorted_reverse(self):
    d = self._dict_unsorted()
    
    d = utils.dict_sorted(d, reverse=True)
    
    for index, key in enumerate(reversed(d.keys())):
      self.assertEqual(key, index)
    
    for index, value in zip(('a', 'b', 'c'), d.values(), strict=True):
      self.assertEqual(index, value)
  
  def test_dict_sorted_value(self):
    d = self._dict_unsorted()
    
    d = utils.dict_sorted(d, key=lambda item: item[1])
    
    for index, key in enumerate(reversed(d.keys())):
      self.assertEqual(key, index)
    
    for index, value in zip(('a', 'b', 'c'), d.values(), strict=True):
      self.assertEqual(index, value)
  
  def test_dict_enumerate(self):
    d = self._dict_unsorted()
    
    self.assertEqual(d, utils.dict_enumerate(d.copy()))
  
  def test_dict_enumerate_list(self):
    d = {0: 'a', 1: 'b', 2: 'c'}
    l = ['a', 'b', 'c']
    
    self.assertEqual(d, dict(utils.dict_enumerate(l)))
  
  def test_dict_once(self):
    d = {}
    
    self.assertTrue(utils.dict_once(d, 'first'))
    self.assertFalse(utils.dict_once(d, 'first'))
    
    self.assertTrue(utils.dict_once(d, 'second'))
    self.assertFalse(utils.dict_once(d, 'second'))
    
    self.assertFalse(utils.dict_once(d, 'first'))
    
    self.assertTrue(utils.dict_once(d, 'third'))
    self.assertFalse(utils.dict_once(d, 'third'))
    
    self.assertFalse(utils.dict_once(d, 'second'))
  
  def test_batched(self):
    b = utils.batched(list(range(200)), 10)
    self.assertEqual(len(list(b)), 20)

if __name__ == '__main__': unittest.main()