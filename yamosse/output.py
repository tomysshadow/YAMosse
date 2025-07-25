from abc import ABC, abstractmethod
from time import time
from os import path
from shlex import quote
import json

import yamosse.utils as yamosse_utils
import yamosse.identification as yamosse_identification

NUMBER_OF_SOUNDS = 'Number of Sounds'
FILE_NAME = 'File Name'
DEFAULT_ITEM_DELIMITER = ' '

EXT_JSON = '.json'.casefold()


def key_number_of_sounds(item):
  result = 0
  
  # the number of sounds, with uncombined timestamps at the end
  for timestamps in item[1].values():
    result += (len(timestamps) ** 2) - sum(isinstance(ts, int) for ts in timestamps) + 1
  
  return result


def key_file_name(item):
  return item[0]


def output(file_name, *args, **kwargs):
  class Output(ABC):
    def __init__(self, file_name, model_yamnet_class_names, identification, subsystem=None):
      if subsystem: self.seconds = time()
      self.subsystem = subsystem
      
      self.sort_by = key_number_of_sounds
      self.sort_reverse = False
      self.item_delimiter = DEFAULT_ITEM_DELIMITER
      self.output_scores = False
      
      self.model_yamnet_class_names = model_yamnet_class_names
      self.identification = yamosse_identification.identification(identification)
      
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
          'log': 'Elapsed Time: %s' % yamosse_utils.hours_minutes(time() - self.seconds)
        })
    
    @abstractmethod
    def options(self, options):
      sort_by = options.sort_by
      
      if sort_by == NUMBER_OF_SOUNDS:
        self.sort_by = key_number_of_sounds
      elif sort_by == FILE_NAME:
        self.sort_by = key_file_name
      
      self._sort_reverse = options.sort_reverse
      
      item_delimiter = yamosse_utils.ascii_backslashreplace(
        yamosse_utils.latin1_unescape(options.item_delimiter))
      
      self.item_delimiter = item_delimiter if item_delimiter else DEFAULT_ITEM_DELIMITER
      self.output_scores = options.output_scores
      return options.output_options
    
    @abstractmethod
    def results(self, results):
      output_scores = self.output_scores
      
      for file_name, identified in results.items():
        if not output_scores:
          identified = {key: list(value.keys()) for key, value in identified.items()}
        
        results[file_name] = yamosse_utils.dict_sorted(identified,
          key=self.identification.key_identified)
    
    @abstractmethod
    def errors(self, errors):
      pass
    
    def _sort(self, results):
      return yamosse_utils.dict_sorted(results, key=self.sort_by, reverse=self.sort_reverse)
  
  class OutputText(Output):
    def options(self, options):
      if not super().options(options): return False
      
      file = self.file
      
      self.print_section('Options')
      options.print(file=file)
      
      print('', file=file)
      return True
    
    def results(self, results):
      if not results: return
      super().results(results)
      
      file = self.file
      
      # print results
      self.print_section('Results')
      self.identification.print_results_to_output(self._sort(results), self)
      
      print('', file=file)
    
    def errors(self, errors):
      if not errors: return
      super().errors(errors)
      
      file = self.file
      
      # print errors
      self.print_section('Errors')
      
      # ascii_backslashreplace replaces Unicode characters with ASCII when printing
      # to prevent crash when run in Command Prompt
      for file_name, ex in errors.items():
        self.print_file(file_name)
        print('\t', yamosse_utils.ascii_backslashreplace(quote(str(ex))), sep='', file=file)
        print('', file=file)
      
      print('', file=file)
    
    def print_section(self, name):
      # name should not contain lines
      # this is an internal method so we trust the class not to pass in a name with lines here
      print('#', name, end='\n\n', file=self.file)
    
    def print_file(self, name):
      print(yamosse_utils.ascii_backslashreplace(quote(name)), file=self.file)
  
  class OutputJSON(Output):
    def __init__(self, *args, **kwargs):
      self._options = None
      self._results = None
      self._errors = None
      
      super().__init__(*args, **kwargs)
    
    def __exit__(self, *args, **kwargs):
      d = {
        'options': self._options,
        'results': self._results,
        'errors': self._errors
      }
      
      json.dump({key: value for key, value in d.items() if value}, self.file, indent=True)
      
      super().__exit__(*args, **kwargs)
    
    def options(self, options):
      output_options = super().options(options)
      
      if output_options:
        self._options = vars(options)
      
      return output_options
    
    def results(self, results):
      super().results(results)
      self._results = self._sort(results)
    
    def errors(self, errors):
      super().errors(errors)
      self._errors = errors
  
  ext = path.splitext(file_name)[1]
  
  if ext.casefold() == EXT_JSON:
    return OutputJSON(file_name, *args, **kwargs)
  
  return OutputText(file_name, *args, **kwargs)