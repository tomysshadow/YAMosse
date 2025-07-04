from abc import ABC, abstractmethod
from time import time
from os import path
from shlex import quote

import yamosse.encoding as yamosse_encoding

NUMBER_OF_SOUNDS = 'Number of Sounds'
FILE_NAME = 'File Name'
DEFAULT_ITEM_DELIMITER = ' '

_ext_json = '.json'.casefold()


def hours_minutes(seconds):
  TO_HMS = 60
  
  m, s = divmod(int(seconds), TO_HMS)
  h, m = divmod(m, TO_HMS)
  
  if h:
    return f'{h:.0f}:{m:02.0f}:{s:02.0f}'
  
  return f'{m:.0f}:{s:02.0f}'


def dict_peek(d):
  return next(iter(d.values()))


def dict_sorted(d, *args, **kwargs):
  return dict(sorted(d.items(), *args, **kwargs))


def key_number_of_sounds(item):
  result = 0
  
  # the number of sounds, with uncombined timestamps at the end
  for timestamps in item[1].values():
    result += (len(timestamps) ** 2) - sum(isinstance(ts, int) for ts in timestamps) + 1
  
  return result


def key_file_name(item):
  return item[0]


def key_class(item):
  return item[0]


def output(file_name, *args, **kwargs):
  class Output(ABC):
    def __init__(self, file_name, model_yamnet_class_names, subsystem=None):
      if subsystem: self.seconds = time()
      self.subsystem = subsystem
      
      self._sort_by = key_number_of_sounds
      self._sort_reverse = False
      self._item_delimiter = DEFAULT_ITEM_DELIMITER
      self._confidence_scores = False
      
      self.model_yamnet_class_names = model_yamnet_class_names
      self.file = open(file_name, 'w')
    
    def __enter__(self):
      return self
    
    def __exit__(self, exc, val, tb):
      self.close()
    
    def close(self):
      self.file.close()
      
      subsystem = self.subsystem
      
      if subsystem:
        subsystem.show(values={
          'log': 'Elapsed Time: %s' % hours_minutes(time() - self.seconds)
        })
    
    @abstractmethod
    def options(self, options):
      sort_by = options.sort_by
      
      if sort_by == NUMBER_OF_SOUNDS:
        self._sort_by = key_number_of_sounds
      elif sort_by == FILE_NAME:
        self._sort_by = key_file_name
      
      self._sort_reverse = options.sort_reverse
      
      item_delimiter = yamosse_encoding.ascii_backslashreplace(
        yamosse_encoding.latin1_unescape(options.item_delimiter))
      
      self._item_delimiter = item_delimiter if item_delimiter else DEFAULT_ITEM_DELIMITER
      self._confidence_scores = options.output_confidence_scores
    
    @abstractmethod
    def results(self, results):
      pass
    
    @abstractmethod
    def errors(self, errors):
      pass
    
    def _sort(self, results):
      return dict_sorted(results, key=self._sort_by, reverse=self._sort_reverse)
  
  class OutputText(Output):
    def options(self, options):
      if options.output_options:
        self._print_section('Options')
        options.print(end='\n\n', file=self.file)
      
      super().options(options)
    
    def results(self, results):
      # sort from least to most timestamps
      results = self._sort(results)
      if not results: return
      
      file = self.file
      model_yamnet_class_names = self.model_yamnet_class_names
      
      # print results
      self._print_section('Results')
      
      # when we are intended to combine all, the timestamp values are empty
      # otherwise, every value will be non-empty
      class_timestamps = dict_peek(results)
      combine_all = not dict_peek(class_timestamps)
      
      for file_name, class_timestamps in results.items():
        self._print_file(file_name)
        
        try:
          if not class_timestamps:
            print('\t', None, file=file)
            continue
          
          if combine_all:
            print('\t', self._item_delimiter.join(
              model_yamnet_class_names[c] for c in class_timestamps.keys()), file=file)
            
            continue
          
          class_timestamps = dict_sorted(class_timestamps, key=key_class)
          
          for class_, timestamp_scores in class_timestamps.items():
            assert timestamp_scores, 'timestamp_scores must not be empty'
            
            print('\t', model_yamnet_class_names[class_], end=':\n', file=file)
            
            for timestamp, score in timestamp_scores.items():
              try: hms = ' - '.join(hours_minutes(t) for t in timestamp)
              except TypeError: hms = hours_minutes(timestamp)
              
              if self._confidence_scores: hms = f'{hms} ({score:.0%})'
              
              timestamp_scores[timestamp] = hms
            
            print('\t\t', self._item_delimiter.join(timestamp_scores.values()), file=file)
        finally:
          print('', file=file)
      
      print('', file=file)
    
    def errors(self, errors):
      if not errors: return
      
      file = self.file
      
      # print errors
      self._print_section('Errors')
      
      # ascii_backslashreplace replaces Unicode characters with ASCII when printing
      # to prevent crash when run in Command Prompt
      for file_name, ex in errors.items():
        self._print_file(file_name)
        print('\t', yamosse_encoding.ascii_backslashreplace(quote(str(ex))), file=file)
        print('', file=file)
      
      print('', file=file)
    
    def _print_section(self, name):
      # name should not contain lines
      # this is an internal method so we trust the class not to pass in a name with lines here
      print('# %s' % name, end='\n\n', file=self.file)
    
    def _print_file(self, name):
      print(yamosse_encoding.ascii_backslashreplace(quote(name)), file=self.file)
  
  ext = path.splitext(file_name)[1]
  
  # not yet implemented
  #if ext.casefold() == _ext_json:
  #  return OutputJSON(file_name, *args, **kwargs)
  return OutputText(file_name, *args, **kwargs)