import pickle
import json
import os
from datetime import datetime

import yamosse.utils as yamosse_utils
import yamosse.identification as yamosse_identification

VERSION = 2

_pickle_file_name = '.'.join((
  os.path.splitext(__file__)[0],
  pickle.__name__
))


class Options:
  class VersionError(ValueError):
    def __init__(self):
      super().__init__('version mismatch')
    
    def __reduce__(self):
      return type(self), (self,)
  
  def __init__(
    self,
    input='', input_device='', input_recursive=False,
    weights='',
    classes=None, calibration=None,
    timespan=3, timespan_span_all=False,
    background_noise_volume=1, background_noise_volume_loglinear=False,
    identification=0,
    confidence_score=50, confidence_score_minmax=False,
    top_ranked=5, top_ranked_output_timestamps=True,
    sort_by='Number of Sounds', sort_reverse=False,
    item_delimiter=', ', indent=True,
    output_options=True, output_scores=False,
    memory_limit=256, max_workers=4, high_priority=True
  ):
    if classes is None: classes = []
    if calibration is None: calibration = []
    
    self.version = VERSION
    
    self.input = input
    self.input_device = input_device
    self.input_recursive = input_recursive
    
    self.weights = weights
    
    self.classes = classes
    self.calibration = calibration
    
    self.timespan = timespan
    self.timespan_span_all = timespan_span_all
    
    self.background_noise_volume = background_noise_volume
    self.background_noise_volume_loglinear = background_noise_volume_loglinear
    
    self.identification = identification
    
    self.confidence_score = confidence_score
    self.confidence_score_minmax = confidence_score_minmax
    
    self.top_ranked = top_ranked
    self.top_ranked_output_timestamps = top_ranked_output_timestamps
    
    self.sort_by = sort_by
    self.sort_reverse = sort_reverse
    self.item_delimiter = item_delimiter
    self.indent = indent
    self.output_options = output_options
    self.output_scores = output_scores
    
    self.memory_limit = memory_limit
    self.max_workers = max_workers
    self.high_priority = high_priority
  
  def print(self, end='\n', file=None):
    #def joined(value):
    #  return value == shlex.join(shlex.split(value))
    
    # this check is disabled because
    # the value of the input field may be temporarily invalid
    # the user can just type anything they want in the entry
    # and that should be fine until it's time to scan
    #assert joined(self.input), 'input must be joined'
    #assert joined(self.weights), 'weights must be joined'
    
    def option(name, value, end='\n'):
      print(name, ': ', value, end=end, sep='', file=file)
    
    option('Current Date/Time', yamosse_utils.ascii_backslashreplace(datetime.now()))
    option('Version', repr(self.version))
    option('Input', yamosse_utils.ascii_backslashreplace(self.input))
    option('Input Device', yamosse_utils.ascii_backslashreplace(self.input_device))
    option('Input Recursive', repr(self.input_recursive))
    option('Weights', yamosse_utils.ascii_backslashreplace(self.weights))
    option('Classes', repr(self.classes))
    option('Calibration', repr(self.calibration))
    option('Timespan', str(self.timespan), end=' seconds\n')
    option('Timespan Span All', repr(self.timespan_span_all))
    option('Background Noise Volume', str(self.background_noise_volume), end='%\n')
    option('Background Noise Volume Log/Linear', repr(self.background_noise_volume_loglinear))
    option('Identification', repr(self.identification))
    option('Confidence Score', str(self.confidence_score), end='%\n')
    option('Confidence Score Min/Max', repr(self.confidence_score_minmax))
    option('Top Ranked', repr(self.top_ranked))
    option('Top Ranked Output Timestamps', repr(self.top_ranked_output_timestamps))
    option('Sort By', repr(self.sort_by))
    option('Sort Reverse', repr(self.sort_reverse))
    option('Item Delimiter', yamosse_utils.ascii_backslashreplace(repr(self.item_delimiter)))
    option('Indent', repr(self.indent))
    option('Output Options', repr(self.output_options))
    option('Output Scores', repr(self.output_scores))
    option('Memory Limit', str(self.memory_limit), end=' MB\n')
    option('Max Workers', repr(self.max_workers))
    option('High Priority', repr(self.high_priority))
    
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
    with open(_pickle_file_name, 'rb') as f:
      options = pickle.load(f)
      
      if options.version != VERSION:
        raise cls.VersionError
      
      return options
  
  def dump(self):
    with open(_pickle_file_name, 'wb') as f:
      pickle.dump(self, f)
  
  def set(self, attrs, strict=True):
    for key, value in vars(self).items():
      if strict or key in attrs:
        setattr(self, key, type(value)(attrs[key]))
  
  @classmethod
  def import_preset(cls, file_name):
    with open(file_name, 'r', encoding='utf8') as f:
      options = cls()
      
      # cast JSON types to Python types
      # presets are expected to have every option
      # this is intended to raise KeyError if a key in preset is missing
      # and likewise, a TypeError if the type couldn't be casted
      options.set(json.load(f))
      
      if options.version != VERSION:
        raise cls.VersionError
      
      return options
  
  def export_preset(self, file_name):
    with open(file_name, 'w', encoding='utf8') as f:
      json.dump(vars(self), f, indent=True)
  
  def volume_loglinear(self, np, volume):
    VOLUME_LOG = 4 # 60 dB
    
    # this intentionally doesn't enforce a dtype
    # so that it will work with any input sound waveform
    # regardless of its format
    if not self.background_noise_volume_loglinear:
      return np.power(volume, VOLUME_LOG)
    
    return volume
  
  def worker(self, np, class_names):
    def single_shot(np, class_names):
      raise RuntimeError('worker is single shot')
    
    self.worker = single_shot
    
    # cast calibration from percentages to floats and ensure it is the right length
    class_names_len = len(class_names)
    calibration = np.divide(self.calibration[:class_names_len], 100.0, dtype=np.float32)
    
    calibration = np.concatenate((calibration,
      np.ones(class_names_len - calibration.size, dtype=np.float32)))
    
    # make background noise volume logarithmic if requested
    background_noise_volume = self.volume_loglinear(np,
      np.divide(self.background_noise_volume, 100.0, dtype=np.float32))
    
    # create a numpy array of this so it can be used with fancy indexing
    self.classes = np.unique(self.classes)
    self.calibration = calibration
    self.background_noise_volume = background_noise_volume
    self.confidence_score /= 100.0
    
    # identification options
    self.identification = yamosse_identification.identification(
      option=self.identification)(self, np)