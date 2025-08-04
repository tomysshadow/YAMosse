import unittest
import tempfile
from os import unlink
from shlex import quote

import yamosse.output as output
import yamosse.options as options
import yamosse.utils as utils

MODEL_YAMNET_CLASS_NAMES = ['Class A', 'Class B', 'Class C', 'Class D', 'Class E']

SUFFIX_TXT = '.txt'
SUFFIX_JSON = '.json'

CONFIDENCE_SCORES_STANDARD = {
  0: {0: 75.0, 3: 50.0, 6: 25.0},
  1: {0: 75.0, 3: 50.0, 6: 25.0},
  2: {0: 75.0, 3: 50.0, 6: 25.0}
}

TOP_RANKED_STANDARD = {
  0: {0: 75.0, 1: 50.0, 2: 25.0},
  3: {0: 75.0, 1: 50.0, 2: 25.0},
  6: {0: 75.0, 1: 50.0, 2: 25.0}
}

class TestOutput:
  def setUp(self, mode='w+b'):
    self.file = tempfile.NamedTemporaryFile(
      mode=mode,
      suffix=SUFFIX_TXT,
      delete=False
    )
  
  def tearDown(self):
    file = self.file
    file.close()
    unlink(file.name)
  
  @staticmethod
  def _file_name_keys(result):
    return {
      'File Name.wav': result,
      'File Name 2.wav': result,
      'File Name 3.wav': result
    }
  
  def _set_options(self, **kwargs):
    o = options.Options()
    o.set(kwargs, strict=False)
    return o
  
  def _output_file(self, identification=0):
    file = self.file
    
    return output.output(
      file.name,
      MODEL_YAMNET_CLASS_NAMES,
      identification
    ), file

class TestOutputText(TestOutput, unittest.TestCase):
  def setUp(self):
    super().setUp(mode='w+')
  
  def test_output_options(self):
    o, f = self._output_file()
    
    with o: o.options(self._set_options())
    
    self.assertEqual(f.readline(), '# Options\n')
    self.assertTrue(f.read().endswith('\n\n'))
  
  def _output_results_cs(self, class_timestamps, **kwargs):
    results = self._file_name_keys(class_timestamps)
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    output_scores = options.output_scores
    
    o, f = self._output_file(0)
    
    with o:
      o.options(options)
      o.results(results)
    
    self.assertEqual(f.readline(), '# Results\n')
    self.assertEqual(f.readline(), '\n')
    
    for file_name in results.keys():
      self.assertEqual(f.readline(), ''.join((quote(file_name), '\n')))
      
      for class_, timestamps in class_timestamps.items():
        self.assertEqual(f.readline(), ''.join(('\t', MODEL_YAMNET_CLASS_NAMES[class_], ':\n')))
        
        if output_scores:
          timestamps = [f'{utils.hours_minutes(ts)} ({s:.0%})' for ts, s in timestamps.items()]
        else:
          timestamps = [utils.hours_minutes(ts) for ts in timestamps]
        
        self.assertEqual(f.readline(), ''.join(('\t\t', item_delimiter.join(timestamps), '\n')))
      
      self.assertEqual(f.readline(), '\n')
    
    self.assertEqual(f.readline(), '\n')
  
  def test_output_results_cs(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD)
  
  def test_output_results_cs_item_delimiter(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, item_delimiter=' . ')
  
  def test_output_results_cs_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, output_scores=True)
  
  def _output_results_tr(self, timestamp_classes, **kwargs):
    results = self._file_name_keys(timestamp_classes)
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    output_scores = options.output_scores
    
    o, f = self._output_file(1)
    
    with o:
      o.options(options)
      o.results(results)
    
    self.assertEqual(f.readline(), '# Results\n')
    self.assertEqual(f.readline(), '\n')
    
    for file_name in results.keys():
      self.assertEqual(f.readline(), ''.join((quote(file_name), '\n')))
      
      for timestamp, classes in timestamp_classes.items():
        if output_scores:
          classes = [f'{MODEL_YAMNET_CLASS_NAMES[c]} ({s:.0%})' for c, s in classes.items()]
        else:
          classes = [MODEL_YAMNET_CLASS_NAMES[c] for c in classes]
        
        self.assertEqual(f.readline(), ''.join(('\t', utils.hours_minutes(timestamp), ': ',
          item_delimiter.join(classes), '\n')))
      
      self.assertEqual(f.readline(), '\n')
    
    self.assertEqual(f.readline(), '\n')
  
  def test_output_results_tr(self):
    self._output_results_tr(TOP_RANKED_STANDARD)
  
  def test_output_results_tr_item_delimiter(self):
    self._output_results_tr(TOP_RANKED_STANDARD, item_delimiter=' . ')
  
  def test_output_results_tr_output_scores(self):
    self._output_results_tr(TOP_RANKED_STANDARD, output_scores=True)
  
  def test_output_errors(self):
    errors = self._file_name_keys('message')
    o, f = self._output_file()
    
    with o: o.errors(errors)
    
    self.assertEqual(f.readline(), '# Errors\n')
    self.assertEqual(f.readline(), '\n')
    
    for file_name, message in errors.items():
      self.assertEqual(f.readline(), ''.join((quote(file_name), '\n')))
      self.assertEqual(f.readline(), ''.join(('\t', quote(message), '\n')))
      self.assertEqual(f.readline(), '\n')
    
    self.assertEqual(f.readline(), '\n')

if __name__ == '__main__': unittest.main()