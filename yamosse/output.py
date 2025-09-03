from abc import ABC, abstractmethod
from time import time
from os.path import splitext
from shlex import quote
import json

import yamosse.utils as yamosse_utils
import yamosse.once as yamosse_once

LINES = ('\r', '\n')

NUMBER_OF_SOUNDS = 'Number of Sounds'
FILE_NAME = 'File Name'
DEFAULT_ITEM_DELIMITER = ' '
DEFAULT_INDENT = '\t'

_ext_json = '.'.join(('', json.__name__)).casefold()


def print_section(name, file=None):
  if yamosse_utils.intersects(LINES, name):
    raise ValueError('name must not contain carriage returns or newlines')
  
  print('#', name, end='\n\n', file=file)


def print_file(name, file=None):
  print(yamosse_utils.ascii_backslashreplace(quote(name)), file=file)


def output(file_name, *args, **kwargs):
  class Output(ABC):
    def __init__(self, file_name, exit_, model_yamnet_class_names, identification,
      subsystem=None, encoding='utf8'):
      if subsystem:
        self._seconds = time()
      
      self.subsystem = subsystem
      
      self.sort_by = identification.key_number_of_sounds
      self.sort_reverse = False
      self.item_delimiter = DEFAULT_ITEM_DELIMITER
      self.indent = DEFAULT_INDENT
      self.output_scores = False
      
      self.top_ranked_output_timestamps = True
      
      self.model_yamnet_class_names = model_yamnet_class_names
      self.identification = identification
      
      self._exit = exit_
      self._file_truncated = False
      self._file = open(file_name, 'a+', encoding=encoding)
    
    def __enter__(self):
      return self
    
    def __exit__(self, exc, val, tb):
      self.close()
    
    def close(self):
      self._file.close()
      
      subsystem = self.subsystem
      
      if subsystem:
        subsystem.show(self._exit, values={
          'log': ': '.join(('Elapsed Time', yamosse_utils.hours_minutes(time() - self._seconds)))
        })
    
    @abstractmethod
    def options(self, options):
      sort_by = options.sort_by
      
      if sort_by == NUMBER_OF_SOUNDS:
        self.sort_by = self.identification.key_number_of_sounds
      elif sort_by == FILE_NAME:
        self.sort_by = self.identification.key_file_name
      
      self.sort_reverse = options.sort_reverse
      
      # this will take any escape characters like \n or \t and make them real characters
      item_delimiter = yamosse_utils.latin1_unescape(options.item_delimiter).encode(
        self._file.encoding, 'backslashreplace').decode()
      
      self.item_delimiter = item_delimiter if item_delimiter else DEFAULT_ITEM_DELIMITER
      self.indent = DEFAULT_INDENT * options.indent
      self.output_scores = options.output_scores
      
      self.top_ranked_output_timestamps = options.top_ranked_output_timestamps
      return options.output_options
    
    @abstractmethod
    def results(self, results):
      # this function makes any changes that are to be applied universally
      # regardless of the identification setting (Confidence Scores or Top Ranked)
      # first, we perform the "Sort By" setting (by Number of Sounds, or File Name)
      items = yamosse_utils.dict_sorted(
        results, key=self.sort_by, reverse=self.sort_reverse).items()
      
      results = []
      output_scores = self.output_scores
      
      for file_name, result in items:
        # if not outputting scores, take them out
        # we take the dictionary (whose values are the scores) and turn its keys into a flat list
        # this is needed for the JSON to be structured correct
        # and when printing these to text, it is also the ideal format
        # because all the timestamps can be simply joined n' printed
        if not output_scores:
          result = {key: list(value.keys()) for key, value in result.items()}
        
        # this sorts the next column - sorting by class/timestamp so that the output is consistent
        results.append({
          'file_name': file_name,
          'result': yamosse_utils.dict_sorted(result,
            key=self.identification.key_result)
        })
      
      return self.identification.restructure_results_for_output(results, self)
    
    @abstractmethod
    def errors(self, errors):
      return errors
    
    @property
    def file(self):
      if not self._file_truncated:
        self._file.truncate(0)
        self._file_truncated = True
      
      return self._file
    
    @property
    def file_truncated(self):
      return self._file_truncated
  
  class OutputText(Output):
    def __init__(self, *args, encoding='ascii', **kwargs):
      self._once = yamosse_once.Once()
      
      super().__init__(*args, encoding=encoding, **kwargs)
    
    def options(self, options):
      if not self._once.add('options'):
        return False
      
      if not super().options(options):
        return False
      
      file = self.file
      
      print_section('Options', file=file)
      options.print(file=file)
      
      print('', file=file)
      return True
    
    def results(self, results):
      if not self._once.add('results'):
        return None
      
      if not results:
        return None
      
      results = super().results(results)
      
      file = self.file
      
      # print results
      print_section('Results', file=file)
      self.identification.print_results_to_output(results, self)
      
      print('', file=file)
      return results
    
    def errors(self, errors):
      if not self._once.add('errors'):
        return None
      
      if not errors:
        return None
      
      errors = super().errors(errors)
      
      file = self.file
      indent = self.indent
      
      # print errors
      print_section('Errors', file=file)
      
      # ascii_backslashreplace replaces Unicode characters with ASCII when printing
      # to prevent crash when run in Command Prompt
      for file_name, ex in errors.items():
        print_file(file_name, file=file)
        print(indent, yamosse_utils.ascii_backslashreplace(quote(str(ex))), sep='', file=file)
        print('', file=file)
      
      print('', file=file)
      return errors
  
  class OutputJSON(Output):
    def __init__(self, *args, **kwargs):
      self._d = {}
      
      # should be called last so file is opened as last step
      super().__init__(*args, **kwargs)
    
    def __exit__(self, exc, val, tb):
      indent = self.indent
      
      # dump anything that is non-empty
      json.dump({key: value for key, value in self._d.items() if value},
        self.file, indent=indent if indent else None)
      
      super().__exit__(exc, val, tb)
    
    def options(self, options):
      if not super().options(options):
        return False
      
      options = vars(options)
      return self._d.setdefault('options', options) is options
    
    def results(self, results):
      return self._d.setdefault('results', super().results(results))
    
    def errors(self, errors):
      return self._d.setdefault('errors', super().errors(errors))
  
  ext = splitext(file_name)[1]
  
  if ext.casefold() == _ext_json:
    return OutputJSON(file_name, *args, **kwargs)
  
  return OutputText(file_name, *args, **kwargs)