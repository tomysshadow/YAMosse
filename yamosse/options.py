import os
import pickle
import json
from datetime import datetime

import yamosse.root as yamosse_root

VERSION = 0
FILE_NAME = 'options.pickle'

_root_file_name = yamosse_root.root(FILE_NAME)

class Options:
  version: int
  
  input: str|tuple
  input_recursive: bool
  weights: str
  
  classes: list
  calibration: list
  
  combine: int
  combine_all: bool
  
  background_noise_volume: int|float
  background_noise_volume_loglinear: bool
  
  identification: int
  
  confidence_score: int|float
  confidence_score_minmax: bool
  
  top_ranked: int
  top_ranked_output_timestamps: bool
  
  sort_by: str
  item_delimiter: str
  output_options: bool
  output_confidence_scores: bool
  
  memory_limit: int
  max_workers: int
  high_priority: bool
  
  class VersionError(ValueError):
    def __init__(self):            
      super().__init__('version mismatch')
    
    def __reduce__(self):
      return (VersionError, (self,))
  
  def __init__(self, input: str|tuple='', input_recursive: bool=False, weights: str='',
    classes: list|None=None, calibration: list|None=None,
    combine: int=3, combine_all: bool=False,
    background_noise_volume: int|float=1, background_noise_volume_loglinear: bool=False,
    identification: int=0,
    confidence_score: int|float=20, confidence_score_minmax: bool=False,
    top_ranked: int=5, top_ranked_output_timestamps: bool=True,
    sort_by: str='Number of Sounds', item_delimiter: str=', ',
    output_options: bool=True, output_confidence_scores: bool=False,
    memory_limit: int=256, max_workers: int=4, high_priority: bool=True):
    if classes == None:
      classes = []
    
    if calibration == None:
      calibration = []
    
    self.version = VERSION
    
    self.input = input
    self.input_recursive = input_recursive
    self.weights = weights
    
    self.classes = classes
    self.calibration = calibration
    
    self.combine = combine
    self.combine_all = combine_all
    
    self.background_noise_volume = background_noise_volume
    self.background_noise_volume_loglinear = background_noise_volume_loglinear
    
    self.identification = identification
    
    self.confidence_score = confidence_score
    self.confidence_score_minmax = confidence_score_minmax
    
    self.top_ranked = top_ranked
    self.top_ranked_output_timestamps = top_ranked_output_timestamps
    
    self.sort_by = sort_by
    self.item_delimiter = item_delimiter
    self.output_options = output_options
    self.output_confidence_scores = output_confidence_scores
    
    self.memory_limit = memory_limit
    self.max_workers = max_workers
    self.high_priority = high_priority
  
  def print(self, end='\n', file=None):
    def print_option(name, value, end='\n'):
      print(': '.join((name, value)), end=end, file=file)
    
    print_option('Current Date/Time', str(datetime.now()))
    print_option('Version', repr(self.version))
    print_option('Input', repr(self.input))
    print_option('Input Recursive', repr(self.input_recursive))
    print_option('Weights', repr(self.weights))
    print_option('Classes', repr(self.classes))
    print_option('Calibration', repr(self.calibration))
    print_option('Combine', str(self.combine), end=' seconds\n')
    print_option('Combine All', repr(self.combine_all))
    print_option('Background Noise Volume', str(self.background_noise_volume), end='%\n')
    print_option('Background Noise Volume Log/Linear', repr(self.background_noise_volume_loglinear))
    print_option('Identification', repr(self.identification))
    print_option('Confidence Score', str(self.confidence_score), end='%\n')
    print_option('Confidence Score Min/Max', repr(self.confidence_score_minmax))
    print_option('Top Ranked', repr(self.top_ranked))
    print_option('Top Ranked Output Timestamps', repr(self.top_ranked_output_timestamps))
    print_option('Sort By', repr(self.sort_by))
    print_option('Item Delimiter', repr(self.item_delimiter))
    print_option('Output Options', repr(self.output_options))
    print_option('Output Confidence Scores', repr(self.output_confidence_scores))
    print_option('Memory Limit', str(self.memory_limit), end=' MB\n')
    print_option('Max Workers', repr(self.max_workers))
    print_option('High Priority', repr(self.high_priority))
    
    print('', end=end, file=file)
  
  def standard_max_workers(self):
    # reserve at least two threads for use by the system
    # unless there are two or less CPU cores, in which case use only one thread
    RESERVED_THREADS = 2
    
    max_workers = os.cpu_count()
    
    if max_workers > RESERVED_THREADS:
      max_workers -= RESERVED_THREADS
    else:
      max_workers = 1
    
    self.max_workers = max_workers
  
  @classmethod
  def load(cls):
    with open(_root_file_name, 'rb') as f:
      options = pickle.load(f)
      
      if options.version != VERSION:
        raise cls.VersionError
      
      return options
  
  def dump(self):
    with open(_root_file_name, 'wb') as f:
      pickle.dump(self, f)
  
  def set(self, items, strict=True):
    for key, value in vars(self).items():
      if strict or key in items:
        setattr(self, key, type(value)(items[key]))
  
  @classmethod
  def import_preset(cls, file_name):
    with open(file_name, 'r') as f:
      options = Options()
      
      # cast JSON types to Python types
      # presets are expected to have every option
      # this is intended to raise KeyError if a key in preset is missing
      # and likewise, a TypeError if the type couldn't be casted
      options.set(json.load(f))
      
      if options.version != VERSION:
        raise cls.VersionError
      
      return options
  
  def export_preset(self, file_name):
    with open(file_name, 'w') as f:
      json.dump(vars(self), f, indent=True)
  
  def initarg(self, input_, model_yamnet_class_names):
    BACKGROUND_NOISE_VOLUME_LOG = 4 # 60 dB
    
    self.input = input_
    
    # must be copied to not interfere with variables
    calibration = self.calibration.copy()
    calibration_len = len(calibration)
    
    for c in range(calibration_len):
      calibration[c] /= 100.0
    
    for c in range(calibration_len, len(model_yamnet_class_names)):
      calibration.insert(c, 1.0)
    
    self.calibration = calibration
    
    if not isinstance(self.background_noise_volume, float):
      self.background_noise_volume /= 100.0
      
      if not self.background_noise_volume_loglinear:
        self.background_noise_volume **= BACKGROUND_NOISE_VOLUME_LOG
    
    if not isinstance(self.confidence_score, float):
      self.confidence_score /= 100.0