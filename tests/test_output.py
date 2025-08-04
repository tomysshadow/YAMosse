import unittest
import tempfile
from os import unlink
from shlex import quote

import yamosse.output as output
import yamosse.options as options

MODEL_YAMNET_CLASS_NAMES = ['Class A', 'Class B', 'Class C', 'Class D', 'Class E']

SUFFIX_TXT = '.txt'
SUFFIX_JSON = '.json'

class TestOutput(unittest.TestCase):
  def setUp(self):
    self.options = options.Options()
    
    self.file = tempfile.NamedTemporaryFile(
      'w+',
      suffix=SUFFIX_TXT,
      delete=False
    )
  
  def tearDown(self):
    file = self.file
    file.close()
    unlink(file.name)
  
  def _output_file(self, identification=0):
    file = self.file
    file.seek(0)
    file.truncate()
    
    return output.output(
      file.name,
      MODEL_YAMNET_CLASS_NAMES,
      identification
    ), file
  
  def test_output_options(self):
    o, f = self._output_file()
    
    with o: o.options(self.options)
    
    self.assertEqual(f.readline(), '# Options\n')
    self.assertTrue(f.read().endswith('\n\n'))
  
  def test_output_results(self):
    CLASS_TIMESTAMPS = {
      0: {0: 75.0, 3: 50.0, 6: 25.0},
      1: {0: 75.0, 3: 50.0, 6: 25.0},
      2: {0: 75.0, 3: 50.0, 6: 25.0}
    }
    
    RESULTS = {
      'File Name.wav': CLASS_TIMESTAMPS,
      'File Name 2.wav': CLASS_TIMESTAMPS
    }
    
    o, f = self._output_file()
    
    with o: o.results(RESULTS)
    
    self.assertEqual(f.readline(), '# Results\n')
    self.assertEqual(f.readline(), '\n')
    
    for file_name in RESULTS.keys():
      self.assertEqual(f.readline(), ''.join((quote(file_name), '\n')))
      
      for class_ in CLASS_TIMESTAMPS.keys():
        self.assertEqual(f.readline(), ''.join(('\t', MODEL_YAMNET_CLASS_NAMES[class_], ':\n')))
        self.assertEqual(f.readline(), ''.join(('\t\t', '0:00 0:03 0:06', '\n')))
      
      self.assertEqual(f.readline(), '\n')
    
    self.assertEqual(f.readline(), '\n')
  
  def test_output_errors(self):
    ERRORS = {
      'File Name.wav': 'message',
      'File Name 2.wav': 'message'
    }
    
    o, f = self._output_file()
    
    with o: o.errors(ERRORS)
    
    self.assertEqual(f.readline(), '# Errors\n')
    self.assertEqual(f.readline(), '\n')
    
    for file_name, message in ERRORS.items():
      self.assertEqual(f.readline(), ''.join((quote(file_name), '\n')))
      self.assertEqual(f.readline(), ''.join(('\t', quote(message), '\n')))
      self.assertEqual(f.readline(), '\n')
    
    self.assertEqual(f.readline(), '\n')

if __name__ == '__main__': unittest.main()