from abc import ABC, abstractmethod
from time import time
from os import path
from shlex import quote

import yamosse.encoding as yamosse_encoding

_ext_json = '.json'.casefold()


def hours_minutes(seconds):
  TO_HMS = 60
  
  m, s = divmod(int(seconds), TO_HMS)
  h, m = divmod(m, TO_HMS)
  
  if h:
    return f'{h:.0f}:{m:02.0f}:{s:02.0f}'
  
  return f'{m:.0f}:{s:02.0f}'


def dict_sorted(d, *args, **kwargs):
  return dict(sorted(d.items(), *args, **kwargs))


def key_number_of_sounds(item):
  result = 0
  
  # the number of sounds, with uncombined timestamps at the end
  for timestamps in item[1].values():
    result += (len(timestamps) ** 2) - sum(isinstance(ts, int) for ts in timestamps) + 1
  
  return result


def key_class(item):
  return item[0]


def output(file_name, *args, **kwargs):
  class Output(ABC):
    def __init__(self, file_name, model_yamnet_class_names, subsystem=None):
      if subsystem: self.seconds = time()
      self.subsystem = subsystem
      
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
    def options(self, value):
      self._confidence_scores = value.output_confidence_scores
    
    @abstractmethod
    def results(self, value):
      pass
    
    @abstractmethod
    def errors(self, value):
      pass
  
  class OutputText(Output):
    def __init__(self, file_name, *args, **kwargs):
      self._item_delimiter = ' '
      
      super().__init__(file_name, *args, **kwargs)
    
    def options(self, value):
      file = self.file
      
      self._print_section('Options')
      value.print(end='\n\n', file=file)
      
      item_delimiter = yamosse_encoding.ascii_backslashreplace(
        yamosse_encoding.latin1_unescape(value.item_delimiter))
      
      if item_delimiter: self._item_delimiter = item_delimiter
      
      super().options(value)
    
    def results(self, value):
      # sort from least to most timestamps
      value = dict_sorted(value, key=key_number_of_sounds)
      if not value: return
      
      file = self.file
      model_yamnet_class_names = self.model_yamnet_class_names
      
      # print results
      self._print_section('Results')
      
      for file_name, class_timestamps in value.items():
        self._print_file(file_name)
        
        if class_timestamps:
          class_timestamps = dict_sorted(class_timestamps, key=key_class)
          
          for class_, timestamp_scores in class_timestamps.items():
            print('\t', model_yamnet_class_names[class_], end=':\n', file=file)
            
            for timestamp, score in timestamp_scores.items():
              try: hms = ' - '.join(hours_minutes(t) for t in timestamp)
              except TypeError: hms = hours_minutes(timestamp)
              
              if self._confidence_scores: hms = f'{hms} ({score:.0%})'
              
              timestamp_scores[timestamp] = hms
            
            print('\t\t', self._item_delimiter.join(timestamp_scores.values()),
              end='\n', file=file)
        else:
          print('\t', None, file=file)
        
        print('', file=file)
      
      print('', file=file)
    
    def errors(self, value):
      if not value: return
      
      file = self.file
      
      # print errors
      self._print_section('Errors')
      
      # ascii_backslashreplace replaces Unicode characters with ASCII when printing
      # to prevent crash when run in Command Prompt
      for file_name, ex in value.items():
        self._print_file(file_name)
        print('\t', yamosse_encoding.ascii_backslashreplace(quote(str(ex))), file=file)
        print('', file=file)
      
      print('', file=file)
    
    def _print_section(self, name):
      # name should not contain lines
      # this is an internal method so we trust the class not to pass in a name with lines here
      print('# %s' % name, end='\n\n', file=self.file)
    
    def _print_file(self, name):
      print(yamosse_encoding.ascii_backslashreplace(quote(name)), end='\n', file=self.file)
  
  ext = path.splitext(file_name)[1]
  
  # not yet implemented
  #if ext.casefold() == _ext_json:
  #  return OutputJSON(file_name, *args, **kwargs)
  
  return OutputText(file_name, *args, **kwargs)