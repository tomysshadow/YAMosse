import unittest
import tempfile
from os import unlink

import yamosse.options as options

import numpy as np

class TestOptions(unittest.TestCase):
  def test_print_ascii(self):
    with tempfile.NamedTemporaryFile(
      mode='w',
      encoding='ascii'
    ) as file:
      o = options.Options()
      
      o.input = "'\u2665'"
      o.weights = '\u2665'
      o.item_delimiter = '\u2665'
      o.print(file=file)
  
  def test_set_types(self):
    o = options.Options()
    
    o.set({'weights': 123, 'calibration': 'string'}, strict=False)
    self.assertIsInstance(o.weights, str)
    self.assertIsInstance(o.calibration, list)
  
  def test_set_strict(self):
    o = options.Options()
    
    try: o.set({'weights': 123, 'calibration': 'string'}, strict=True)
    except KeyError: return
    
    raise Exception('set should raise KeyError if strict is True')
  
  def test_export_import_preset(self):
    file = tempfile.NamedTemporaryFile(
      mode='w+',
      encoding='utf8',
      delete=False
    )
    
    try:
      exported = options.Options()
      exported.export_preset(file.name)
      
      file.seek(0)
      
      imported = options.Options.import_preset(file.name)
      self.assertEqual(vars(exported), vars(imported))
    finally:
      file.close()
      unlink(file.name)
  
  def test_worker(self):
    o = options.Options()
    o.classes = [1, 1, 2, 3, 3, 3]
    o.calibration = [1, 2, 3]
    
    o.background_noise_volume = 50
    o.background_noise_volume_loglinear = False
    
    o.confidence_score = 50
    
    o.worker(np, ['Class A', 'Class B', 'Class C', 'Class D', 'Class E'])
    
    self.assertEqual(o.classes.size, 3)
    self.assertEqual(o.calibration.size, 5)
    self.assertTrue(o.background_noise_volume < 1.0)
    self.assertFalse(o.background_noise_volume == 0.5)
    self.assertTrue(o.confidence_score < 1.0)
    
    try:
      o.worker(np, ['Class A', 'Class B', 'Class C', 'Class D', 'Class E'])
    except RuntimeError: return
    
    raise Exception('worker should be single shot')

if __name__ == '__main__': unittest.main()