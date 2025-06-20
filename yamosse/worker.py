import atexit
import os
import csv

import soundfile as sf

import yamosse.root as yamosse_root

MODEL_YAMNET_DIR = os.path.join('models', 'research', 'audioset', 'yamnet')
MODEL_YAMNET_CLASS_MAP_CSV = 'yamnet_class_map.csv'
MODEL_YAMNET_WEIGHTS_URL = 'https://storage.googleapis.com/audioset/yamnet.h5'

TFHUB_YAMNET_MODEL_URL = 'https://www.kaggle.com/models/google/yamnet/TensorFlow2/yamnet/1'

MONO = 1

_shutdown = None
_options = None

_patch_hop_seconds = 0.48
_patch_window_seconds = 0.96
_sample_rate = 16000.0

_yamnet = None

_root_model_yamnet_dir = yamosse_root.root(MODEL_YAMNET_DIR)
_tfhub_enabled = not os.path.isdir(_root_model_yamnet_dir)


def class_names(class_map_csv=''):
  if not class_map_csv:
    class_map_csv = yamosse_root.root(MODEL_YAMNET_CLASS_MAP_CSV
      ) if _tfhub_enabled else os.path.join(_root_model_yamnet_dir, MODEL_YAMNET_CLASS_MAP_CSV)
  
  # alternate method that does not depend on Tensorflow
  with open(class_map_csv) as csv_file:
    reader = csv.reader(csv_file)
    next(reader) # skip header
    return list(display_name for (_, _, display_name) in reader)


def tfhub_enabled():
  return _tfhub_enabled


def tfhub_cache(dir_='tfhub_modules'):
  if not _tfhub_enabled:
    return None
  
  # use our own cache
  # I don't like every program on the system all intermingling with
  # everybody else's models
  # if two programs request the same model at the same time
  # it's unclear if I could end up with
  # the half downloaded/half extracted model from the other program
  root_tfhub_cache_dir = yamosse_root.root(dir_)
  os.environ['TFHUB_CACHE_DIR'] = root_tfhub_cache_dir
  return root_tfhub_cache_dir


def initializer(worker, receiver, sender, shutdown, options,
  model_yamnet_class_names, tfhub_enabled):
  global _shutdown
  global _options
  
  global _patch_hop_seconds
  global _patch_window_seconds
  global _sample_rate
  
  global _yamnet
  
  global _tfhub_enabled
  
  CONFIDENCE_SCORE = 0
  TOP_RANKED = 1
  
  # for Linux, child process inherits receiver pipe from parent
  # so the receiver instance must be closed explicitly here
  # as for the sender... supposedly it would get garbage collected
  # (somehow I don't trust it, would rather just do it explicitly)
  atexit.register(sender.close)
  receiver.close()
  
  _shutdown = shutdown
  if shutdown.is_set(): return
  
  # seperated out because loading the worker dependencies (mainly Tensorflow) in
  # the main process consumes a non-trivial amount of memory for no benefit
  # and causes startup to take significantly longer
  import sys
  
  try:
    import tf_keras
  except ImportError:
    # for Windows, where we can't use tf_keras with GPU Acceleration
    from tensorflow import keras
    sys.modules['tf_keras'] = keras
  
  import tensorflow as tf
  import psutil
  
  assert _tfhub_enabled == tfhub_enabled, 'tfhub_enabled mismatch'
  
  if options.high_priority:
    current_process = psutil.Process(os.getpid())
    current_process.nice(psutil.HIGH_PRIORITY_CLASS)
  
  gpus = tf.config.list_physical_devices('GPU')
  
  # memory limit is per-worker, so for multiple GPUs we need to divide amongst them
  if gpus:
    memory_limit = options.memory_limit // len(gpus)
    
    logical_device_configuration = [
      tf.config.LogicalDeviceConfiguration(memory_limit=memory_limit)
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
  
  # TODO: if tfhub not enabled, and weights not set, ask to download here under worker lock
  # don't continue if answer is no
  # otherwise, should show download progress in window
  with worker.get_lock():
    if tfhub_enabled:
      if not worker.value:
        # the first time YAMNet is downloaded it may have to download and extract
        # so print a message then so the user knows what's going on
        # consequent loads should be faster
        sender.send({
          'log': 'Loading YAMNet, please wait...'
        })
      
      # this is done under the worker lock because
      # the docs don't clarify if this is safe to call
      # from multiple processes at the same time
      # from a cursory look at the source code, it looks like there are
      # attempts to safeguard for that, but only for downloading and not extracting
      # i.e. two processes won't download at the same time, but if one
      # begins extracting it's possible to get the half extracted result
      # either way docs don't mention any of this, so I'm slapping my own lock on it
      yamnet = tfhub.load(TFHUB_YAMNET_MODEL_URL)
    
    worker.value += 1
    
    sender.send({
      'log': 'Worker #%d: GPU Acceleration %s' % (worker.value, 'Enabled' if gpus else 'Disabled')
    })
  
  if tfhub_enabled:
    # confirm that the model has the same classes we expect
    assert class_names(yamnet.class_map_path().numpy()
      ) == model_yamnet_class_names, 'model_yamnet_class_names mismatch'
  else:
    params = yamnet_params.Params()
    _patch_hop_seconds = params.patch_hop_seconds
    _patch_window_seconds = params.patch_window_seconds
    _sample_rate = params.sample_rate
    
    yamnet = yamnet_model.yamnet_frames_model(params)
    
    if not options.weights:
      raise NotImplementedError('TODO') # TODO: offer download
    
    yamnet.load_weights(options.weights)
  
  _options = options
  _yamnet = yamnet


def worker_confidence_score(class_predictions, prediction, score, options):
  calibration = options.calibration
  confidence_score = options.confidence_score
  
  for class_ in options.classes:
    calibrated_score = score[class_] * calibration[class_]
    
    if calibrated_score >= confidence_score:
      prediction_scores = class_predictions.setdefault(class_, {})
      
      prediction_scores[prediction] = max(
        prediction_scores.get(prediction, calibrated_score), calibrated_score)


def worker_class_timestamps(class_predictions, shutdown, combine):
  # create timestamps from predictions/scores
  results = {}
  
  for class_, prediction_scores in class_predictions.items():
    if _shutdown.is_set(): return None
    
    timestamp_scores = {}
    
    begin = 0
    end = 0
    
    score_begin = 0
    score_end = 0
    
    predictions = list(prediction_scores.keys())
    predictions_len = len(predictions)
    
    scores = list(prediction_scores.values())
    
    for prediction_end in range(1, predictions_len + 1):
      end = predictions[score_end] + 1
      
      if prediction_end == predictions_len or end < predictions[prediction_end]:
        begin = predictions[score_begin]
        
        # the cast to float here is to convert a potential Tensorflow or Numpy dtype
        # into a Python native type, because we want to pickle this result into the main process
        # which does not have those modules loaded
        timestamp_scores[(begin, end) if begin + combine < end else begin] = float(max(
          scores[score_begin:score_end + 1]))
        
        score_begin = prediction_end
      
      score_end = prediction_end
    
    results[class_] = timestamp_scores
  
  return results


def worker(file_name):
  global _shutdown
  global _options
  
  global _patch_hop_seconds
  global _patch_window_seconds
  global _sample_rate
  
  global _yamnet
  
  shutdown = _shutdown
  if shutdown.is_set(): return None
  
  with sf.SoundFile(file_name) as f:
    # the main offenders for startup time
    # (thankfully doing these imports here doesn't seem to slow down worker performance much)
    import numpy as np
    import tensorflow as tf
    import resampy
    
    # Decode the WAV file.
    results = {}
    seconds = 0.0
    
    options = _options
    combine = options.combine
    background_noise_volume = options.background_noise_volume
    
    patch_hop_seconds = _patch_hop_seconds
    patch_window_seconds = _patch_window_seconds
    sample_rate = _sample_rate
    
    yamnet = _yamnet
    
    # blocks() expects number of samples
    # so convert the seconds values into the equivalent number of samples
    # this should truncate to int, don't round the number
    # otherwise YAMNet may get confused and think it's two patches when it's meant to be one
    sr = f.samplerate
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
        worker_confidence_score(results, int(seconds), score, options)
        seconds += patch_hop_seconds
  
  return worker_class_timestamps(results, shutdown, combine)