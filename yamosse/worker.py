import sys
import atexit
import os
import csv

import soundfile as sf

import yamosse.root as yamosse_root

PROGRESSBAR_MAXIMUM = 100

MODEL_YAMNET_DIR = os.path.join('models', 'research', 'audioset', 'yamnet')
MODEL_YAMNET_CLASS_MAP_CSV = 'yamnet_class_map.csv'
MODEL_YAMNET_WEIGHTS_URL = 'https://storage.googleapis.com/audioset/yamnet.h5'
MODEL_YAMNET_WEIGHTS_PATH = 'yamnet.h5'

TFHUB_YAMNET_MODEL_URL = 'https://www.kaggle.com/models/google/yamnet/TensorFlow2/yamnet/1'

SAMPLE_RATE = 16000
MONO = 1

_initializer_ex = None

_step = None
_steps = None
_sender = None

_shutdown = None
_options = None

_sample_rate = float(SAMPLE_RATE)
_patch_window_seconds = 0.96
_patch_hop_seconds = 0.48

_yamnet = None

_root_model_yamnet_dir = yamosse_root.root(MODEL_YAMNET_DIR)
_tfhub_enabled = not os.path.isdir(_root_model_yamnet_dir)


def _high_priority(psutil=None):
  if psutil:
    psutil.Process().nice(psutil.HIGH_PRIORITY_CLASS)
    return
  
  # try and decrease the niceness until we eventually hit a limit or error out
  # as far as I can tell this is necessary because, without root permissions
  # setting it too low and ending up below the RLIMIT just fails without doing anything
  MIN_NICE = -20
  
  try:
    for priority in reversed(range(MIN_NICE, os.getpriority(os.PRIO_PROCESS, 0))):
      os.setpriority(os.PRIO_PROCESS, 0, priority)
  except OSError:
    pass


def _step_progress(worker_step, current_step=1.0):
  current_step = int(current_step * PROGRESSBAR_MAXIMUM) - worker_step
  
  if current_step <= 0:
    return worker_step
  
  previous_step = 0
  worker_step += current_step
  next_step = 0
  
  step = _step
  steps = _steps
  
  with step.get_lock():
    previous_step = step.value
    step.value += current_step
    next_step = step.value
  
  previous_progress = int(previous_step / steps * PROGRESSBAR_MAXIMUM) + 1
  next_progress = int(next_step / steps * PROGRESSBAR_MAXIMUM) + 1
  
  for current_progress in range(previous_progress, next_progress):
    _sender.send({
      'progressbar': {
        'set': {'args': (current_progress,)}
      },
      
      'log': '%d%% complete' % current_progress
    })
  
  return worker_step


def class_names(class_map_csv=''):
  if not class_map_csv:
    if _tfhub_enabled:
      class_map_csv = yamosse_root.root(MODEL_YAMNET_CLASS_MAP_CSV)
    else:
      class_map_csv = os.path.join(_root_model_yamnet_dir, MODEL_YAMNET_CLASS_MAP_CSV)
  
  # alternate method that does not depend on TensorFlow
  with open(class_map_csv, 'r', encoding='utf8') as csv_file:
    reader = csv.reader(csv_file)
    next(reader) # skip header
    return [display_name for (_, _, display_name) in reader]


def tfhub_enabled():
  return _tfhub_enabled


def tfhub_cache(dir_='tfhub_modules'):
  if not _tfhub_enabled: return None
  
  # use our own cache
  # I don't like every program on the system all intermingling with
  # everybody else's models
  # if two programs request the same model at the same time
  # it's unclear if I could end up with
  # the half downloaded/half extracted model from the other program
  root_tfhub_cache_dir = yamosse_root.root(dir_)
  os.environ['TFHUB_CACHE_DIR'] = root_tfhub_cache_dir
  return root_tfhub_cache_dir


def initializer(number, step, steps, receiver, sender, shutdown, options,
  model_yamnet_class_names, tfhub_enabled):
  global _initializer_ex
  
  global _step
  global _steps
  global _sender
  
  global _shutdown
  global _options
  
  global _sample_rate
  global _patch_window_seconds
  global _patch_hop_seconds
  
  global _yamnet
  
  try:
    # for Linux, child process inherits receiver pipe from parent
    # so the receiver instance must be closed explicitly here
    # as for the sender... supposedly it would get garbage collected
    # (somehow I don't trust it, would rather just do it explicitly)
    atexit.register(sender.close)
    receiver.close()
    
    _shutdown = shutdown
    if shutdown.is_set(): return
    
    assert _tfhub_enabled == tfhub_enabled, 'tfhub_enabled mismatch'
    
    # seperated out because loading the worker dependencies (mainly TensorFlow) in
    # the main process consumes a non-trivial amount of memory for no benefit
    # and causes startup to take significantly longer
    try:
      import tf_keras
    except ImportError:
      # for Windows, where we can't use tf_keras with GPU Acceleration
      from tensorflow import keras
      sys.modules['tf_keras'] = keras
    
    import numpy as np
    import tensorflow as tf
    
    # Python's built in modules are fine for setting priority on Linux
    # otherwise we require psutil
    # we require this even if we are not setting the process priority to high
    # because it should be highlighted to you that you're missing the module early on
    # in case you ever do decide to check the box to do it
    psutil = None
    
    # this is used instead of platform.system() here because this is what truly determines
    # the availability of setpriority on the os module
    if os.name != 'posix':
      import psutil
    
    options.worker(np, model_yamnet_class_names)
    
    if options.high_priority:
      _high_priority(psutil)
    
    # currently, setting a per-CPU memory limit isn't supported by TensorFlow
    # however in future the 'GPU' argument could be removed if it does ever become supported
    # (then error handling/logging would need to be added here for compatibility with old versions)
    gpus = tf.config.list_physical_devices('GPU')
    
    if gpus:
      logical_device_configuration = [
        tf.config.LogicalDeviceConfiguration(memory_limit=options.memory_limit)
      ]
      
      for gpu in gpus:
        tf.config.set_logical_device_configuration(
          gpu,
          logical_device_configuration
        )
    
    if tfhub_enabled:
      import tensorflow_hub as tfhub
    else:
      # this sucks but I can't do anything about it
      # the repo version doesn't include an __init__.py, so I can't just relative import it
      # but I still want it linked as a git submodule so it'll get updates
      # so it needs to be on sys.path, there's no way around it
      sys.path.append(_root_model_yamnet_dir)
      
      import params as yamnet_params
      import yamnet as yamnet_model
    
    yamnet = None
    
    with number.get_lock():
      if tfhub_enabled:
        if not number.value:
          # the first time YAMNet is downloaded it may have to download and extract
          # so print a message then so the user knows what's going on
          # consequent loads should be faster
          sender.send({
            'log': 'Loading YAMNet, please wait...'
          })
        
        # this is done under the number lock because
        # the docs don't clarify if this is safe to call
        # from multiple processes at the same time
        # from a cursory look at the source code, it looks like there are
        # attempts to safeguard for that, but only for downloading and not extracting
        # i.e. two processes won't download at the same time, but if one
        # begins extracting it's possible to get the half extracted result
        # either way docs don't mention any of this, so I'm slapping my own lock on it
        yamnet = tfhub.load(TFHUB_YAMNET_MODEL_URL)
      
      number.value += 1
      
      sender.send({
        'log': 'Worker #%d: GPU Acceleration %s' % (number.value,
          'Enabled' if gpus else 'Disabled')
      })
    
    if tfhub_enabled:
      # confirm that the model has the same classes we expect
      assert class_names(yamnet.class_map_path().numpy()
        ) == model_yamnet_class_names, 'model_yamnet_class_names mismatch'
    else:
      params = yamnet_params.Params()
      _sample_rate = params.sample_rate
      
      patch_window_seconds = params.patch_window_seconds
      
      assert patch_window_seconds > 0.0, 'patch_window_seconds must be greater than zero'
      assert patch_window_seconds <= 1.0, 'patch_window_seconds must be less than or equal to one'
      
      patch_hop_seconds = params.patch_hop_seconds
      
      assert patch_hop_seconds > 0.0, 'patch_hop_seconds must be greater than zero'
      assert patch_hop_seconds <= patch_window_seconds, ('patch_hop_seconds must be less than or '
        'equal to patch_window_seconds')
      
      _patch_window_seconds = patch_window_seconds
      _patch_hop_seconds = patch_hop_seconds
      
      yamnet = yamnet_model.yamnet_frames_model(params)
      
      weights = options.weights
      assert weights, 'weights must not be empty'
      
      yamnet.load_weights(weights)
    
    _step = step
    _steps = steps
    _sender = sender
    
    _options = options
    _yamnet = yamnet
  except:
    _initializer_ex = sys.exc_info()


def worker(file_name):
  # the main process can only see exception tracebacks from the worker, not initializer
  # so we raise it here to make it visible to the main process
  if _initializer_ex:
    exc, val, tb = _initializer_ex
    raise val
  
  shutdown = _shutdown
  if shutdown.is_set(): return None
  
  options = _options
  identification = options.identification
  background_noise_volume = options.background_noise_volume
  
  step = 0
  
  try:
    with (identification, sf.SoundFile(file_name) as f):
      # the main offenders for startup time
      # (thankfully doing these imports here doesn't seem to slow down worker performance much)
      import numpy as np
      import tensorflow as tf
      import resampy
      
      # Decode the WAV file.
      seconds = 0.0
      
      sample_rate = _sample_rate
      patch_window_seconds = _patch_window_seconds
      patch_hop_seconds = _patch_hop_seconds
      
      yamnet = _yamnet
      
      # blocks() expects number of samples
      # so convert the seconds values into the equivalent number of samples
      # this should truncate to int, don't round the number
      # otherwise YAMNet may get confused and think it's two patches when it's meant to be one
      sr = f.samplerate
      seconds_steps = f.frames / sr
      overlap = int(sr * patch_hop_seconds)
      blocksize = int(sr * patch_window_seconds) + overlap
      
      # dtypes
      int16_tf = tf.int16
      int16 = int16_tf.as_numpy_dtype
      float32 = np.float32
      float32_int16_max = float32(int16_tf.max)
      
      # reading the entire sound file at once can cause an out of memory error
      # so instead we read it in blocks that match YAMNet's patch size
      # we request int16 so the sound is normalized
      # (because we want it to be, and it won't be if float64/float32 are requested)
      # then we convert it back to float via division
      for waveform in f.blocks(overlap=overlap, blocksize=blocksize, dtype=int16):
        # should I check this every loop? Would a variable to keep track actually save time...?
        if shutdown.is_set(): return None
        
        step = _step_progress(step, seconds / seconds_steps)
        
        assert waveform.dtype == int16, 'Bad sample type: %r' % waveform.dtype
        
        # Convert to mono and the sample rate expected by YAMNet.
        if waveform.ndim == MONO:
          waveform = np.divide(waveform, float32_int16_max, dtype=float32)
        else:
          waveform = waveform.mean(axis=MONO, dtype=float32)
          np.divide(waveform, float32_int16_max, out=waveform)
        
        if sr != sample_rate:
          waveform = resampy.resample(waveform, sr, sample_rate)
        
        # skip background noise
        # this isn't strictly necessary but dramatically boosts performance
        # this must be done here in this function, because this is a super hot path
        # (calling another function here, even an inner function, causes significant overhead)
        if background_noise_volume and not np.greater_equal(
          np.abs(waveform), background_noise_volume).any():
          seconds += patch_window_seconds
          continue
        
        # Predict YAMNet classes.
        for score in yamnet(waveform)[0]:
          identification.predict((int(seconds), np.array(score, dtype=float32)))
          seconds += patch_hop_seconds
      
      return identification.timestamps(shutdown)
  finally:
    _step_progress(step)