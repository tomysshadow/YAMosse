from abc import ABC, abstractmethod
from time import time
from os.path import splitext
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
  
  # the number of sounds, with timespans at the end
  for timestamps in item[1].values():
    result += (len(timestamps) ** 2) - sum(isinstance(ts, int) for ts in timestamps) + 1
  
  return result


def key_file_name(item):
  return item[0]


def output(file_name, *args, **kwargs):
  class Output(ABC):
    def __init__(self, file_name, model_yamnet_class_names, identification,
      subsystem=None, encoding='utf8'):
      if subsystem: self.seconds = time()
      self.subsystem = subsystem
      
      self.sort_by = key_number_of_sounds
      self.sort_reverse = False
      self.item_delimiter = DEFAULT_ITEM_DELIMITER
      self.output_scores = False
      
      self.top_ranked_output_timestamps = True
      
      self.model_yamnet_class_names = model_yamnet_class_names
      self.identification = yamosse_identification.identification(option=identification)
      
      self.file = open(file_name, 'w', encoding=encoding)
    
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
      
      self.sort_reverse = options.sort_reverse
      
      # this will take any escape characters like \n or \t and make them real characters
      item_delimiter = yamosse_utils.latin1_unescape(options.item_delimiter).encode(
        self.file.encoding, 'backslashreplace').decode()
      
      self.item_delimiter = item_delimiter if item_delimiter else DEFAULT_ITEM_DELIMITER
      self.output_scores = options.output_scores
      
      self.top_ranked_output_timestamps = options.top_ranked_output_timestamps
      return options.output_options
    
    @abstractmethod
    def results(self, results):
      # this function makes any changes that are to be applied universally
      # regardless of the identification setting (Confidence Scores or Top Ranked)
      # first, we perform the "Sort By" setting (by Number of Sounds, or File Name)
      results = yamosse_utils.dict_sorted(results, key=self.sort_by, reverse=self.sort_reverse)
      
      output_scores = self.output_scores
      
      for file_name, result in results.items():
        # if not outputting scores, take them out
        # we take the dictionary (whose values are the scores) and turn its keys into a flat list
        # this is needed for the JSON to be structured correct
        # and when printing these to text, it is also the ideal format
        # because all the timestamps can be simply joined n' printed
        if not output_scores:
          result = {key: list(value.keys()) for key, value in result.items()}
        
        # this sorts the next column - sorting by class/timestamp so that the output is consistent
        results[file_name] = yamosse_utils.dict_sorted(result,
          key=self.identification.key_result)
      
      return self.identification.hms(results)
    
    @abstractmethod
    def errors(self, errors):
      return errors
  
  class OutputText(Output):
    def __init__(self, *args, encoding='ascii', **kwargs):
      super().__init__(*args, encoding=encoding, **kwargs)
    
    def options(self, options):
      if not super().options(options): return False
      
      file = self.file
      
      self.print_section('Options')
      options.print(file=file)
      
      print('', file=file)
      return True
    
    def results(self, results):
      if not results: return None
      results = super().results(results)
      
      file = self.file
      
      # print results
      self.print_section('Results')
      self.identification.print_results_to_output(results, self)
      
      print('', file=file)
      return results
    
    def errors(self, errors):
      if not errors: return None
      errors = super().errors(errors)
      
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
      return errors
    
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
      
      # should be called last so file is opened as last step
      super().__init__(*args, **kwargs)
    
    def __exit__(self, *args, **kwargs):
      d = {
        'options': self._options,
        'results': self._results,
        'errors': self._errors
      }
      
      # dump anything that is non-empty
      json.dump({key: value for key, value in d.items() if value}, self.file, indent=True)
      
      super().__exit__(*args, **kwargs)
    
    def options(self, options):
      output_options = super().options(options)
      
      if output_options:
        self._options = vars(options)
      
      return output_options
    
    def results(self, results):
      results = super().results(results)
      self._results = results
      return results
    
    def errors(self, errors):
      errors = super().errors(errors)
      self._errors = errors
      return errors
  
  ext = splitext(file_name)[1]
  
  if ext.casefold() == EXT_JSON:
    return OutputJSON(file_name, *args, **kwargs)
  
  return OutputText(file_name, *args, **kwargs)