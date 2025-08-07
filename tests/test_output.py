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

FILE_NAMES = ('File Name A.wav', 'File Name B.wav', 'File Name C.wav')

CONFIDENCE_SCORES_STANDARD = {
  'File Name A.wav': {
    0: {0: 75.0},
    1: {0: 75.0, 3: 50.0},
    2: {0: 75.0, 3: 50.0, 6: 25.0}
  },
  
  'File Name B.wav': {
    0: {0: 75.0},
    1: {0: 75.0, 3: 50.0}
  },
  
  'File Name C.wav': {
    0: {0: 75.0}
  }
}

CONFIDENCE_SCORES_TIMESPANS = {
  0: {
    (1, 5): 75.0
  },
  1: {
    (1, 5): 75.0,
    7: 50.0
  },
  2: {
    (1, 5): 75.0,
    7: 50.0,
    (9, 12): 25.0
  }
}

TOP_RANKED_STANDARD = {
  'File Name A.wav': {
    0: {0: 75.0, 1: 50.0, 2: 25.0},
    3: {1: 75.0, 2: 50.0, 3: 25.0},
    6: {2: 75.0, 3: 50.0, 4: 25.0}
  },
  
  'File Name B.wav': {
    0: {0: 75.0, 1: 50.0, 2: 25.0},
    3: {1: 75.0, 2: 50.0, 3: 25.0}
  },
  
  'File Name C.wav': {
    0: {0: 75.0, 1: 50.0, 2: 25.0}
  }
}

TOP_RANKED_TIMESPANS = {
  (1, 5): {0: 75.0, 1: 50.0, 2: 25.0},
  7: {1: 75.0, 2: 50.0, 3: 25.0},
  (9, 12): {2: 75.0, 3: 50.0, 4: 25.0}
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
    d = {}
    
    for file_name in FILE_NAMES:
      d[file_name] = result
    
    return d
  
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
  
  def _output_results_cs(self, results, **kwargs):
    results_output = None
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    
    indent = '\t' * options.indent
    indent2 = indent * 2
    
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
        self.assertEqual(f.readline(), ''.join((indent, MODEL_YAMNET_CLASS_NAMES[class_], ':\n')))
        
        if output_scores:
          timestamps = [f'{t["timestamp"]} ({t["score"]:.0%})' for t in timestamps]
        
        self.assertEqual(f.readline(), ''.join((indent2, item_delimiter.join(timestamps), '\n')))
      
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
    self._output_results_cs(self._file_name_keys(CONFIDENCE_SCORES_TIMESPANS),
      sort_by=output.NUMBER_OF_SOUNDS, timespan=3, output_scores=False)
  
  def test_output_results_cs_nos_timespans_output_scores(self):
    self._output_results_cs(self._file_name_keys(CONFIDENCE_SCORES_TIMESPANS),
      sort_by=output.NUMBER_OF_SOUNDS, timespan=3, output_scores=True)
  
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
    self._output_results_cs(self._file_name_keys(CONFIDENCE_SCORES_TIMESPANS),
      sort_by=output.FILE_NAME, timespan=3, output_scores=False)
  
  def test_output_results_cs_fn_timespans_output_scores(self):
    self._output_results_cs(self._file_name_keys(CONFIDENCE_SCORES_TIMESPANS),
      sort_by=output.FILE_NAME, timespan=3, output_scores=True)
  
  def _output_results_tr(self, results, **kwargs):
    results_output = None
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    indent = '\t' * options.indent
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
        
        self.assertEqual(f.readline(), ''.join((indent, top_score['timestamp'], ': ',
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
    self._output_results_tr(self._file_name_keys(TOP_RANKED_TIMESPANS),
      sort_by=output.NUMBER_OF_SOUNDS, timespan=3, output_scores=False)
  
  def test_output_results_tr_nos_timespans_output_scores(self):
    self._output_results_tr(self._file_name_keys(TOP_RANKED_TIMESPANS),
      sort_by=output.NUMBER_OF_SOUNDS, timespan=3, output_scores=True)
  
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
    self._output_results_tr(self._file_name_keys(TOP_RANKED_TIMESPANS),
      sort_by=output.FILE_NAME, timespan=3, output_scores=False)
  
  def test_output_results_tr_fn_timespans_output_scores(self):
    self._output_results_tr(self._file_name_keys(TOP_RANKED_TIMESPANS),
      sort_by=output.FILE_NAME, timespan=3, output_scores=True)
  
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
  
  def _output_results_cs(self, results, **kwargs):
    results_output = None
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    output_scores = options.output_scores
    
    o, f = self._output_file(0)
    
    with o:
      self.assertFalse(o.options(options))
      results_output = o.results(results)
    
    d = json.loads(f.read())
    results_output_str = results_output.copy()
    
    for file_name, classes_timestamps in results_output_str.items():
      results_output_str[file_name] = dict(zip([str(c) for c in classes_timestamps.keys()],
        classes_timestamps.values()))
    
    self.assertEqual(d['results'], results_output_str)
    return results_output
  
  def test_output_results_cs_nos(self):
    r = self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=False)
    
    i = iter(r.values())
    
    classes = next(i)
    
    self.assertEqual(classes[0], ['0:00'])
    
    classes = next(i)
    
    self.assertEqual(classes[0], ['0:00'])
    self.assertEqual(classes[1], ['0:00', '0:03'])
    
    classes = next(i)
    
    self.assertEqual(classes[0], ['0:00'])
    self.assertEqual(classes[1], ['0:00', '0:03'])
    self.assertEqual(classes[2], ['0:00', '0:03', '0:06'])
  
  def test_output_results_cs_nos_item_delimiter(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      item_delimiter=' . ')
  
  def test_output_results_cs_nos_output_scores(self):
    r = self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=True)
    
    i = iter(r.values())
    
    classes = next(i)
    
    self.assertEqual(classes[0], [
      {'timestamp': '0:00', 'score': 75.0}
    ])
    
    classes = next(i)
    
    self.assertEqual(classes[0], [
      {'timestamp': '0:00', 'score': 75.0}
    ])
    
    self.assertEqual(classes[1], [
      {'timestamp': '0:00', 'score': 75.0},
      {'timestamp': '0:03', 'score': 50.0}
    ])
    
    classes = next(i)
    
    self.assertEqual(classes[0], [
      {'timestamp': '0:00', 'score': 75.0}
    ])
    
    self.assertEqual(classes[1], [
      {'timestamp': '0:00', 'score': 75.0},
      {'timestamp': '0:03', 'score': 50.0}
    ])
    
    self.assertEqual(classes[2], [
      {'timestamp': '0:00', 'score': 75.0},
      {'timestamp': '0:03', 'score': 50.0},
      {'timestamp': '0:06', 'score': 25.0}
    ])
  
  def test_output_results_cs_nos_timespans(self):
    r = self._output_results_cs(self._file_name_keys(CONFIDENCE_SCORES_TIMESPANS),
      sort_by=output.NUMBER_OF_SOUNDS, timespan=3, output_scores=False)
    
    for classes in r.values():
      self.assertEqual(classes[0], ['0:01 - 0:05'])
      self.assertEqual(classes[1], ['0:01 - 0:05', '0:07'])
      self.assertEqual(classes[2], ['0:01 - 0:05', '0:07', '0:09 - 0:12'])
  
  def test_output_results_cs_nos_timespans_output_scores(self):
    r = self._output_results_cs(self._file_name_keys(CONFIDENCE_SCORES_TIMESPANS),
      sort_by=output.NUMBER_OF_SOUNDS, timespan=3, output_scores=True)
    
    file_name, classes = utils.dict_peekitem(r)
    
    self.assertEqual(classes[0], [
      {'timestamp': '0:01 - 0:05', 'score': 75.0}
    ])
    
    self.assertEqual(classes[1], [
      {'timestamp': '0:01 - 0:05', 'score': 75.0},
      {'timestamp': '0:07', 'score': 50.0}
    ])
    
    self.assertEqual(classes[2], [
      {'timestamp': '0:01 - 0:05', 'score': 75.0},
      {'timestamp': '0:07', 'score': 50.0},
      {'timestamp': '0:09 - 0:12', 'score': 25.0}
    ])
  
  def test_output_results_cs_fn(self):
    r = self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      output_scores=False)
    
    i = iter(r.values())
    
    classes = next(i)
    
    self.assertEqual(classes[0], ['0:00'])
    self.assertEqual(classes[1], ['0:00', '0:03'])
    self.assertEqual(classes[2], ['0:00', '0:03', '0:06'])
    
    classes = next(i)
    
    self.assertEqual(classes[0], ['0:00'])
    self.assertEqual(classes[1], ['0:00', '0:03'])
    
    classes = next(i)
    
    self.assertEqual(classes[0], ['0:00'])
  
  def test_output_results_cs_fn_item_delimiter(self):
    self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      item_delimiter=' . ')
  
  def test_output_results_cs_fn_output_scores(self):
    r = self._output_results_cs(CONFIDENCE_SCORES_STANDARD, sort_by=output.FILE_NAME,
      output_scores=True)
    
    i = iter(r.values())
    
    classes = next(i)
    
    self.assertEqual(classes[0], [
      {'timestamp': '0:00', 'score': 75.0}
    ])
    
    self.assertEqual(classes[1], [
      {'timestamp': '0:00', 'score': 75.0},
      {'timestamp': '0:03', 'score': 50.0}
    ])
    
    self.assertEqual(classes[2], [
      {'timestamp': '0:00', 'score': 75.0},
      {'timestamp': '0:03', 'score': 50.0},
      {'timestamp': '0:06', 'score': 25.0}
    ])
    
    classes = next(i)
    
    self.assertEqual(classes[0], [
      {'timestamp': '0:00', 'score': 75.0}
    ])
    
    self.assertEqual(classes[1], [
      {'timestamp': '0:00', 'score': 75.0},
      {'timestamp': '0:03', 'score': 50.0}
    ])
    
    classes = next(i)
    
    self.assertEqual(classes[0], [
      {'timestamp': '0:00', 'score': 75.0}
    ])
  
  def test_output_results_cs_fn_timespans(self):
    r = self._output_results_cs(self._file_name_keys(CONFIDENCE_SCORES_TIMESPANS),
      sort_by=output.FILE_NAME, timespan=3, output_scores=False)
    
    for classes in r.values():
      self.assertEqual(classes[0], ['0:01 - 0:05'])
      self.assertEqual(classes[1], ['0:01 - 0:05', '0:07'])
      self.assertEqual(classes[2], ['0:01 - 0:05', '0:07', '0:09 - 0:12'])
  
  def test_output_results_cs_fn_timespans_output_scores(self):
    r = self._output_results_cs(self._file_name_keys(CONFIDENCE_SCORES_TIMESPANS),
      sort_by=output.FILE_NAME, timespan=3, output_scores=True)
    
    file_name, classes = utils.dict_peekitem(r)
    
    self.assertEqual(classes[0], [
      {'timestamp': '0:01 - 0:05', 'score': 75.0}
    ])
    
    self.assertEqual(classes[1], [
      {'timestamp': '0:01 - 0:05', 'score': 75.0},
      {'timestamp': '0:07', 'score': 50.0}
    ])
    
    self.assertEqual(classes[2], [
      {'timestamp': '0:01 - 0:05', 'score': 75.0},
      {'timestamp': '0:07', 'score': 50.0},
      {'timestamp': '0:09 - 0:12', 'score': 25.0}
    ])
  
  def _output_results_tr(self, results, **kwargs):
    results_output = None
    
    options = self._set_options(output_options=False, **kwargs)
    item_delimiter = options.item_delimiter
    output_scores = options.output_scores
    
    o, f = self._output_file(1)
    
    with o:
      self.assertFalse(o.options(options))
      results_output = o.results(results)
    
    d = json.loads(f.read())
    results_output_copy = results_output.copy()
    
    if output_scores:
      for top_scores in results_output_copy.values():
        for top_score in top_scores:
          classes = top_score['classes']
          
          top_score['classes'] = dict(zip([str(c) for c in classes.keys()],
            classes.values()))
    
    self.assertEqual(d['results'], results_output_copy)
    return results_output
  
  def test_output_results_tr_nos(self):
    r = self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=False)
    
    i = iter(r.values())
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': [0, 1, 2]})
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': [0, 1, 2]})
    self.assertEqual(timestamps[1], {'timestamp': '0:03', 'classes': [1, 2, 3]})
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': [0, 1, 2]})
    self.assertEqual(timestamps[1], {'timestamp': '0:03', 'classes': [1, 2, 3]})
    self.assertEqual(timestamps[2], {'timestamp': '0:06', 'classes': [2, 3, 4]})
  
  def test_output_results_tr_nos_item_delimiter(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      item_delimiter=' . ')
  
  def test_output_results_tr_nos_output_scores(self):
    r = self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.NUMBER_OF_SOUNDS,
      output_scores=True)
    
    i = iter(r.values())
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': {
      '0': 75.0,
      '1': 50.0,
      '2': 25.0
    }})
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': {
      '0': 75.0,
      '1': 50.0,
      '2': 25.0
    }})
    
    self.assertEqual(timestamps[1], {'timestamp': '0:03', 'classes': {
      '1': 75.0,
      '2': 50.0,
      '3': 25.0
    }})
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': {
      '0': 75.0,
      '1': 50.0,
      '2': 25.0
    }})
    
    self.assertEqual(timestamps[1], {'timestamp': '0:03', 'classes': {
      '1': 75.0,
      '2': 50.0,
      '3': 25.0
    }})
    
    self.assertEqual(timestamps[2], {'timestamp': '0:06', 'classes': {
      '2': 75.0,
      '3': 50.0,
      '4': 25.0
    }})
  
  def test_output_results_tr_nos_timespans(self):
    r = self._output_results_tr(self._file_name_keys(TOP_RANKED_TIMESPANS),
      sort_by=output.NUMBER_OF_SOUNDS, timespan=3, output_scores=False)
    
    for timestamps in r.values():
      self.assertEqual(timestamps[0], {'timestamp': '0:01 - 0:05', 'classes': [0, 1, 2]})
      self.assertEqual(timestamps[1], {'timestamp': '0:07', 'classes': [1, 2, 3]})
      self.assertEqual(timestamps[2], {'timestamp': '0:09 - 0:12', 'classes': [2, 3, 4]})
  
  def test_output_results_tr_nos_timespans_output_scores(self):
    r = self._output_results_tr(self._file_name_keys(TOP_RANKED_TIMESPANS),
      sort_by=output.NUMBER_OF_SOUNDS, timespan=3, output_scores=True)
    
    for timestamps in r.values():
      self.assertEqual(timestamps[0], {'timestamp': '0:01 - 0:05', 'classes': {
        '0': 75.0,
        '1': 50.0,
        '2': 25.0
      }})
      
      self.assertEqual(timestamps[1], {'timestamp': '0:07', 'classes': {
        '1': 75.0,
        '2': 50.0,
        '3': 25.0
      }})
      
      self.assertEqual(timestamps[2], {'timestamp': '0:09 - 0:12', 'classes': {
        '2': 75.0,
        '3': 50.0,
        '4': 25.0
      }})
  
  def test_output_results_tr_fn(self):
    r = self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      output_scores=False)
    
    i = iter(r.values())
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': [0, 1, 2]})
    self.assertEqual(timestamps[1], {'timestamp': '0:03', 'classes': [1, 2, 3]})
    self.assertEqual(timestamps[2], {'timestamp': '0:06', 'classes': [2, 3, 4]})
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': [0, 1, 2]})
    self.assertEqual(timestamps[1], {'timestamp': '0:03', 'classes': [1, 2, 3]})
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': [0, 1, 2]})
  
  def test_output_results_tr_fn_item_delimiter(self):
    self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      item_delimiter=' . ')
  
  def test_output_results_tr_fn_output_scores(self):
    r = self._output_results_tr(TOP_RANKED_STANDARD, sort_by=output.FILE_NAME,
      output_scores=True)
    
    i = iter(r.values())
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': {
      '0': 75.0,
      '1': 50.0,
      '2': 25.0
    }})
    
    self.assertEqual(timestamps[1], {'timestamp': '0:03', 'classes': {
      '1': 75.0,
      '2': 50.0,
      '3': 25.0
    }})
    
    self.assertEqual(timestamps[2], {'timestamp': '0:06', 'classes': {
      '2': 75.0,
      '3': 50.0,
      '4': 25.0
    }})
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': {
      '0': 75.0,
      '1': 50.0,
      '2': 25.0
    }})
    
    self.assertEqual(timestamps[1], {'timestamp': '0:03', 'classes': {
      '1': 75.0,
      '2': 50.0,
      '3': 25.0
    }})
    
    timestamps = next(i)
    
    self.assertEqual(timestamps[0], {'timestamp': '0:00', 'classes': {
      '0': 75.0,
      '1': 50.0,
      '2': 25.0
    }})
  
  def test_output_results_tr_fn_timespans(self):
    r = self._output_results_tr(self._file_name_keys(TOP_RANKED_TIMESPANS),
      sort_by=output.FILE_NAME, timespan=3, output_scores=False)
    
    for timestamps in r.values():
      self.assertEqual(timestamps[0], {'timestamp': '0:01 - 0:05', 'classes': [0, 1, 2]})
      self.assertEqual(timestamps[1], {'timestamp': '0:07', 'classes': [1, 2, 3]})
      self.assertEqual(timestamps[2], {'timestamp': '0:09 - 0:12', 'classes': [2, 3, 4]})
  
  def test_output_results_tr_fn_timespans_output_scores(self):
    r = self._output_results_tr(self._file_name_keys(TOP_RANKED_TIMESPANS),
      sort_by=output.FILE_NAME, timespan=3, output_scores=True)
    
    for timestamps in r.values():
      self.assertEqual(timestamps[0], {'timestamp': '0:01 - 0:05', 'classes': {
        '0': 75.0,
        '1': 50.0,
        '2': 25.0
      }})
      
      self.assertEqual(timestamps[1], {'timestamp': '0:07', 'classes': {
        '1': 75.0,
        '2': 50.0,
        '3': 25.0
      }})
      
      self.assertEqual(timestamps[2], {'timestamp': '0:09 - 0:12', 'classes': {
        '2': 75.0,
        '3': 50.0,
        '4': 25.0
      }})
  
  def test_output_errors(self):
    errors = self._file_name_keys('message')
    o, f = self._output_file()
    
    with o: o.errors(errors)
    
    d = json.loads(f.read())
    
    for message in d['errors'].values():
      self.assertEqual(message, 'message')

if __name__ == '__main__': unittest.main()