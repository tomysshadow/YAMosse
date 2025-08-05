import unittest
from abc import ABC
import tempfile
from os import unlink
from shlex import quote
import json

import yamosse.output as output
import yamosse.options as options
import yamosse.utils as utils

MODEL_YAMNET_CLASS_NAMES = ['Class A', 'Class B', 'Class C', 'Class D', 'Class E']

SUFFIX_TXT = '.txt'
SUFFIX_JSON = '.json'

CONFIDENCE_SCORES_STANDARD = {
  0: {0: 75.0},
  1: {0: 75.0, 3: 50.0},
  2: {0: 75.0, 3: 50.0, 6: 25.0}
}

CONFIDENCE_SCORES_TIMESPANS = {
  0: {
    (1, 3): 75.0
  },
  1: {
    (1, 3): 75.0,
    5: 50.0
  },
  2: {
    (1, 3): 75.0,
    5: 50.0,
    (7, 12): 25.0
  }
}

TOP_RANKED_STANDARD = {
  0: {0: 75.0, 1: 50.0, 2: 25.0},
  3: {1: 75.0, 2: 50.0, 3: 25.0},
  6: {2: 75.0, 3: 50.0, 4: 25.0}
}

TOP_RANKED_TIMESPANS = {
  (1, 3): {0: 75.0, 1: 50.0, 2: 25.0},
  5: {1: 75.0, 2: 50.0, 3: 25.0},
  (7, 12): {2: 75.0, 3: 50.0, 4: 25.0}
}

class TestOutput(ABC):
  def setUp(self, suffix):
    self.file = tempfile.NamedTemporaryFile(
      mode='w+',
      suffix=suffix,
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
    super().setUp(SUFFIX_TXT)
  
  def test_output_options(self):
    o, f = self._output_file()
    
    with o: o.options(self._set_options())
    
    self.assertEqual(f.readline(), '# Options\n')
    self.assertTrue(f.read().endswith('\n\n'))
  
  def _output_results_cs(self, class_timestamps, **kwargs):
    results = self._file_name_keys(class_timestamps)
    results_output = None
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    output_scores = options.output_scores
    
    o, f = self._output_file(0)
    
    with o:
      self.assertFalse(o.options(options))
      results_output = o.results(results)
    
    self.assertEqual(f.readline(), '# Results\n')
    self.assertEqual(f.readline(), '\n')
    
    for file_name, class_timestamps in results_output.items():
      self.assertEqual(f.readline(), ''.join((quote(file_name), '\n')))
      
      for class_, timestamps in class_timestamps.items():
        self.assertEqual(f.readline(), ''.join(('\t', MODEL_YAMNET_CLASS_NAMES[class_], ':\n')))
        
        if output_scores:
          timestamps = [f'{t["timestamp"]} ({t["score"]:.0%})' for t in timestamps]
        
        self.assertEqual(f.readline(), ''.join(('\t\t', item_delimiter.join(timestamps), '\n')))
      
      self.assertEqual(f.readline(), '\n')
    
    self.assertEqual(f.readline(), '\n')
  
  def test_output_results_cs_nos(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=False)
  
  def test_output_results_cs_nos_item_delimiter(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      item_delimiter=' . ')
  
  def test_output_results_cs_nos_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=True)
  
  def test_output_results_cs_nos_timespans(self):
    self._output_results_cs(CONFIDENCE_SCORES_TIMESPANS, sort_by=output.NUMBER_OF_SOUNDS,
      timespan=3, output_scores=False)
  
  def test_output_results_cs_nos_timespans_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_TIMESPANS, sort_by=output.NUMBER_OF_SOUNDS,
      timespan=3, output_scores=True)
  
  def test_output_results_cs_fn(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      output_scores=False)
  
  def test_output_results_cs_fn_item_delimiter(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      item_delimiter=' . ')
  
  def test_output_results_cs_fn_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      output_scores=True)
  
  def test_output_results_cs_fn_timespans(self):
    self._output_results_cs(CONFIDENCE_SCORES_TIMESPANS, sort_by=output.FILE_NAME,
      timespan=3, output_scores=False)
  
  def test_output_results_cs_fn_timespans_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_TIMESPANS, sort_by=output.FILE_NAME,
      timespan=3, output_scores=True)
  
  def _output_results_tr(self, timestamp_classes, **kwargs):
    results = self._file_name_keys(timestamp_classes)
    results_output = None
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    output_scores = options.output_scores
    
    o, f = self._output_file(1)
    
    with o:
      self.assertFalse(o.options(options))
      results_output = o.results(results)
    
    self.assertEqual(f.readline(), '# Results\n')
    self.assertEqual(f.readline(), '\n')
    
    for file_name, top_scores in results_output.items():
      self.assertEqual(f.readline(), ''.join((quote(file_name), '\n')))
      
      for top_score in top_scores:
        classes = top_score['classes']
        
        if output_scores:
          classes = [f'{MODEL_YAMNET_CLASS_NAMES[c]} ({s:.0%})' for c, s in classes.items()]
        else:
          classes = [MODEL_YAMNET_CLASS_NAMES[c] for c in classes]
        
        self.assertEqual(f.readline(), ''.join(('\t', top_score['timestamp'], ': ',
          item_delimiter.join(classes), '\n')))
      
      self.assertEqual(f.readline(), '\n')
    
    self.assertEqual(f.readline(), '\n')
  
  def test_output_results_tr_nos(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=False)
  
  def test_output_results_tr_nos_item_delimiter(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      item_delimiter=' . ')
  
  def test_output_results_tr_nos_output_scores(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=True)
  
  def test_output_results_tr_nos_timespans(self):
    self._output_results_tr(TOP_RANKED_TIMESPANS, sort_by=output.NUMBER_OF_SOUNDS,
      timespan=3, output_scores=False)
  
  def test_output_results_tr_nos_timespans_output_scores(self):
    self._output_results_tr(TOP_RANKED_TIMESPANS, sort_by=output.NUMBER_OF_SOUNDS,
      timespan=3, output_scores=True)
  
  def test_output_results_tr_fn(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      output_scores=False)
  
  def test_output_results_tr_fn_item_delimiter(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      item_delimiter=' . ')
  
  def test_output_results_tr_fn_output_scores(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      output_scores=True)
  
  def test_output_results_tr_fn_timespans(self):
    self._output_results_tr(TOP_RANKED_TIMESPANS, sort_by=output.FILE_NAME,
      timespan=3, output_scores=False)
  
  def test_output_results_tr_fn_timespans_output_scores(self):
    self._output_results_tr(TOP_RANKED_TIMESPANS, sort_by=output.FILE_NAME,
      timespan=3, output_scores=True)
  
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

class TestOutputJSON(TestOutput, unittest.TestCase):
  def setUp(self):
    super().setUp(SUFFIX_JSON)
  
  def test_output_options(self):
    o, f = self._output_file()
    
    with o: o.options(self._set_options())
    
    d = json.loads(f.read())
    self.assertIn('options', d)
  
  def _output_results_cs(self, class_timestamps, **kwargs):
    results = self._file_name_keys(class_timestamps)
    results_output = None
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    output_scores = options.output_scores
    
    o, f = self._output_file(0)
    
    with o:
      self.assertFalse(o.options(options))
      results_output = o.results(results)
    
    d = json.loads(f.read())
    
    for file_name, classes_timestamps in results_output.items():
      results_output[file_name] = dict(zip([str(c) for c in classes_timestamps.keys()],
        classes_timestamps.values()))
    
    self.assertEqual(d['results'], results_output)
    return results_output
  
  def test_output_results_cs_nos(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=False)
  
  def test_output_results_cs_nos_item_delimiter(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      item_delimiter=' . ')
  
  def test_output_results_cs_nos_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=True)
  
  def test_output_results_cs_nos_timespans(self):
    self._output_results_cs(CONFIDENCE_SCORES_TIMESPANS, sort_by=output.NUMBER_OF_SOUNDS,
      timespan=3, output_scores=False)
  
  def test_output_results_cs_nos_timespans_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_TIMESPANS, sort_by=output.NUMBER_OF_SOUNDS,
      timespan=3, output_scores=True)
  
  def test_output_results_cs_fn(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      output_scores=False)
  
  def test_output_results_cs_fn_item_delimiter(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      item_delimiter=' . ')
  
  def test_output_results_cs_fn_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      output_scores=True)
  
  def test_output_results_cs_fn_timespans(self):
    self._output_results_cs(CONFIDENCE_SCORES_TIMESPANS, sort_by=output.FILE_NAME,
      timespan=3, output_scores=False)
  
  def test_output_results_cs_fn_timespans_output_scores(self):
    self._output_results_cs(CONFIDENCE_SCORES_TIMESPANS, sort_by=output.FILE_NAME,
      timespan=3, output_scores=True)
  
  def _output_results_tr(self, timestamp_classes, **kwargs):
    results = self._file_name_keys(timestamp_classes)
    results_output = None
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    output_scores = options.output_scores
    
    o, f = self._output_file(1)
    
    with o:
      self.assertFalse(o.options(options))
      results_output = o.results(results)
    
    d = json.loads(f.read())
    
    if output_scores:
      for top_scores in results_output.values():
        for top_score in top_scores:
          classes = top_score['classes']
          
          top_score['classes'] = dict(zip([str(c) for c in classes.keys()],
            classes.values()))
    
    self.assertEqual(d['results'], results_output)
    return results_output
  
  def test_output_results_tr_nos(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=False)
  
  def test_output_results_tr_nos_item_delimiter(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      item_delimiter=' . ')
  
  def test_output_results_tr_nos_output_scores(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=True)
  
  def test_output_results_tr_nos_timespans(self):
    self._output_results_tr(TOP_RANKED_TIMESPANS, sort_by=output.NUMBER_OF_SOUNDS,
      timespan=3, output_scores=False)
  
  def test_output_results_tr_nos_timespans_output_scores(self):
    self._output_results_tr(TOP_RANKED_TIMESPANS, sort_by=output.NUMBER_OF_SOUNDS,
      timespan=3, output_scores=True)
  
  def test_output_results_tr_fn(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      output_scores=False)
  
  def test_output_results_tr_fn_item_delimiter(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      item_delimiter=' . ')
  
  def test_output_results_tr_fn_output_scores(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      output_scores=True)
  
  def test_output_results_tr_fn_timespans(self):
    self._output_results_tr(TOP_RANKED_TIMESPANS, sort_by=output.FILE_NAME,
      timespan=3, output_scores=False)
  
  def test_output_results_tr_fn_timespans_output_scores(self):
    self._output_results_tr(TOP_RANKED_TIMESPANS, sort_by=output.FILE_NAME,
      timespan=3, output_scores=True)
  
  def test_output_errors(self):
    errors = self._file_name_keys('message')
    o, f = self._output_file()
    
    with o: o.errors(errors)
    
    d = json.loads(f.read())
    
    for message in d['errors'].values():
      self.assertEqual(message, 'message')

if __name__ == '__main__': unittest.main()