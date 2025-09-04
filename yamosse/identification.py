from abc import ABC, abstractmethod
from collections import OrderedDict

import yamosse.utils as yamosse_utils
import yamosse.output as yamosse_output

IDENTIFICATION_CONFIDENCE_SCORE = 0
IDENTIFICATION_TOP_RANKED = 1

TIMESTAMP_ALL = -1

HMS_ALL = 'All'
HMS_TIMESPAN = ' - '


class _Identification(ABC):
  __slots__ = ('options', 'np')
  
  def __init__(self, options, np):
    self.options = options
    self.np = np
  
  def __enter__(self):
    return self
  
  def __exit__(self, exc, val, tb):
    self.clear()
  
  @abstractmethod
  def clear(self):
    pass
  
  @abstractmethod
  def predict(self, prediction_score=None):
    pass
  
  @abstractmethod
  def timestamps(self, shutdown):
    pass
  
  @staticmethod
  def _range_timestamp(begin, end, timespan):
    return (begin, end) if timespan and begin + timespan < end else begin
  
  @classmethod
  def restructure_results_for_output(cls, results, output):
    assert output # silence unused argument warning
    return results
  
  @classmethod
  @abstractmethod
  def print_results_to_output(cls, results, output):
    raise NotImplementedError
  
  @classmethod
  def hms(cls, timestamp):
    # substitute TIMESTAMP_ALL for HMS_ALL
    if timestamp == TIMESTAMP_ALL:
      return HMS_ALL
    
    # convert to HMS string and join the timestamps if this is a timespan
    try:
      return HMS_TIMESPAN.join(yamosse_utils.hours_minutes(t) for t in timestamp)
    except TypeError:
      pass
    
    return yamosse_utils.hours_minutes(timestamp)
  
  @classmethod
  def key_number_of_sounds(cls, item):
    result = 0
    
    # the number of sounds, with timespans at the end
    for timestamps in item:
      result += (
        (len(timestamps) ** 2)
        - sum(isinstance(ts, int) for ts in timestamps)
        + 1
      )
    
    return result
  
  @classmethod
  def key_file_name(cls, item):
    return item[0]
  
  @classmethod
  def key_result(cls, item):
    # this function is used from Output
    # to sort the column of results that's tabbed in once (one column to the right of file names)
    # that is, classes in Confidence Score mode, or timestamps in Top Ranked mode
    return item[0]


class _IdentificationConfidenceScore(_Identification):
  __slots__ = ('_class_predictions', '_minmax')
  
  def __init__(self, options, np):
    super().__init__(options, np)
    
    self._class_predictions = {}
    self._minmax = self._max if options.confidence_score_minmax else self._min
  
  def clear(self):
    self._class_predictions.clear()
  
  def predict(self, prediction_score=None):
    if not prediction_score: return
    
    class_predictions = self._class_predictions
    prediction, score = prediction_score
    
    options = self.options
    calibration = options.calibration
    confidence_score = options.confidence_score
    
    if options.timespan_span_all:
      prediction = TIMESTAMP_ALL
    
    # this is pretty self explanatory
    # check if the score we got is above the confidence score
    # if it is, take the max score found per one second of the sound
    # for display if the Output Scores option is checked
    for class_ in options.classes:
      # calibrate the score and ensure it is less than 100%
      calibrated_score = min(score[class_] * calibration[class_], 1.0)
      
      if not self._minmax(calibrated_score, confidence_score):
        continue
      
      prediction_scores = class_predictions.setdefault(class_, {})
      
      prediction_scores[prediction] = max(
        prediction_scores.get(prediction, calibrated_score), calibrated_score)
  
  def timestamps(self, shutdown):
    # create timestamps from predictions/scores
    class_timestamps = {}
    timespan = self.options.timespan
    
    for class_, prediction_scores in self._class_predictions.items():
      if shutdown.is_set(): return None
      
      timestamp_scores = {}
      
      begin = 0
      end = 0
      
      score_begin = 0
      score_end = 0
      
      predictions = list(prediction_scores.keys())
      predictions_len = len(predictions)
      
      scores = list(prediction_scores.values())
      
      for prediction in range(1, predictions_len + 1):
        end = predictions[score_end] + 1
        
        if prediction == predictions_len or end < predictions[prediction]:
          begin = predictions[score_begin]
          
          # the cast to float here is to convert a potential TensorFlow or Numpy dtype
          # into a Python native type, because we want to pickle this result
          # into the main process which does not have those modules loaded
          timestamp = self._range_timestamp(begin, end, timespan)
          timestamp_scores[timestamp] = float(max(scores[score_begin:score_end + 1]))
          
          score_begin = prediction
        
        score_end = prediction
      
      # class is cast to int for same reason as above (it might come from a numpy array)
      class_timestamps[int(class_)] = timestamp_scores
    
    return class_timestamps
  
  @classmethod
  def restructure_results_for_output(cls, results, output):
    for file_name_result in results:
      class_timestamps = file_name_result['result']
      
      for class_, timestamps in class_timestamps.items():
        if not isinstance(timestamps, dict):
          continue
        
        # if Output Scores is checked, timestamps will be a dictionary
        # for JSON that won't preserve insertion order, so we need to make it a list
        timestamps = [{'timestamp': ts, 'score': s} for ts, s in timestamps.items()]
        class_timestamps[class_] = timestamps
    
    return results
  
  @classmethod
  def print_results_to_output(cls, results, output):
    file = output.file
    model_yamnet_class_names = output.model_yamnet_class_names
    item_delimiter = output.item_delimiter
    
    indent = output.indent
    indent2 = indent * 2
    
    output_scores = output.output_scores
    
    for file_name_result in results:
      yamosse_output.print_file(file_name_result['file_name'], file=file)
      
      class_timestamps = file_name_result['result']
      
      # this try-finally is just to ensure the newline is always printed even when continuing
      try:
        # if no timestamps were found for this file, then print None for this file
        if not class_timestamps:
          print(indent, None, sep='', file=file)
          continue
        
        # a list of classes with 'All' timestamps, including the associated scores if available
        all_timestamps = []
        
        for class_, timestamps in class_timestamps.items():
          class_name = model_yamnet_class_names[class_]
          
          # try and get the 'All' timestamp, if it exists
          # if it doesn't, just catch the error and move on
          all_timestamp = None
          
          if output_scores:
            for t, timestamp_score in enumerate(timestamps):
              if timestamp_score['timestamp'] == TIMESTAMP_ALL:
                all_timestamp = (class_name, timestamps.pop(t))
                break
          else:
            try:
              timestamps.remove(TIMESTAMP_ALL)
            except ValueError:
              pass
            else:
              all_timestamp = class_name
          
          if all_timestamp is not None:
            assert not timestamps, 'timestamps must be empty if Span All is checked'
            
            all_timestamps.append(all_timestamp)
            continue
          
          if output_scores:
            timestamps = [f'{cls.hms(t["timestamp"])} ({t["score"]:.0%})' for t in timestamps]
          else:
            timestamps = [cls.hms(t) for t in timestamps]
          
          print(indent, class_name, ':\n', indent2,
            item_delimiter.join(timestamps), sep='', file=file)
        
        if all_timestamps:
          # in this case we want to print the class names and scores, but not timestamps
          if output_scores:
            all_timestamps = [f'{c} ({t["score"]:.0%})' for c, t in all_timestamps]
          
          print(indent, item_delimiter.join(all_timestamps), sep='', file=file)
      finally:
        print('', file=file)
  
  @classmethod
  def key_number_of_sounds(cls, item):
    return super().key_number_of_sounds(item[1].values())
  
  @staticmethod
  def _min(calibrated_score, confidence_score):
    return calibrated_score >= confidence_score
  
  @staticmethod
  def _max(calibrated_score, confidence_score):
    return calibrated_score < confidence_score


class _IdentificationTopRanked(_Identification):
  __slots__ = ('_top_scores', '_calibration')
  
  def __init__(self, options, np):
    super().__init__(options, np)
    
    self._top_scores = {}
    self._calibration = np.take(options.calibration, options.classes)
  
  def clear(self):
    self._top_scores.clear()
  
  def predict(self, prediction_score=None):
    np = self.np
    
    options = self.options
    classes = options.classes
    
    # top should be zero (not None) by default
    # this is what ensures the timer starts at zero
    top = 0
    scores = []
    top_scores = self._top_scores
    
    # get the last top scores, if any
    # this is so we can convert them into their final dictionary form later
    if top_scores:
      top, scores = yamosse_utils.dict_peekitem(top_scores)
    
    # score and default are both initialized to the same value
    # later, we will be checking if default is score to determine
    # if a new item was added to top_scores or not
    score = None
    default = score
    
    # if we have a new prediction/score
    # round down predictions to nearest timespan
    # we also only take the scores we specifically care about (saves memory)
    # we will be able to get them back later by indexing into the classes array
    if prediction_score:
      prediction, score = prediction_score
      score = np.minimum(score.take(classes) * self._calibration, 1.0, dtype=np.float32)
      
      # in the span all case, we actually just want to list
      # every class that is ever in the top ranked as one big summary
      # so we don't bother with the whole numpy stacking thing
      # we also don't care about timestamps in this case
      # so the TIMESTAMP_ALL key is used exclusively
      if options.timespan_span_all:
        class_scores = top_scores.setdefault(TIMESTAMP_ALL, OrderedDict())
        class_indices = score.argsort()[::-1][:options.top_ranked]
        
        # here we need to go back to storing this as a stock Python list
        # as we need to expand it with new scores, so a numpy array wouldn't cut it
        # (or at least, wouldn't be efficient with all the copying of arrays)
        for class_index in class_indices:
          scores = class_scores.setdefault(int(classes[class_index]), [])
          scores.append(score[class_index]) # must append so it mutates
        
        return
      
      if top > prediction:
        raise ValueError('prediction invalid (expected %d or greater, got %d)' % (
          top, prediction))
      
      timespan = options.timespan
      
      # when timespan is zero, prediction should always be set to its initial value
      # this tells the location of the first sound identified, which is useful information
      if timespan:
        prediction = prediction // timespan * timespan
      elif top_scores:
        prediction = top
      
      score = [score]
      default = top_scores.setdefault(int(prediction), score)
    elif options.timespan_span_all:
      # this only happens on the last call, from the timestamps method
      # (when prediction_score is None)
      # we use this opportunity to convert top_scores into its final form
      # specifically, to find averages for all of the scores for each class
      class_scores = top_scores[TIMESTAMP_ALL]
      
      for class_, scores in class_scores.items():
        class_scores[class_] = float(np.mean(scores, axis=0, dtype=np.float32))
      
      # normally numpy's argsort function handles the sorting directly on the arrays
      # but now we've averaged the scores so it's all outta whack
      # so we gotta sort it now again
      # just using the stock Python functions this time, because now this is a dictionary
      top_scores[TIMESTAMP_ALL] = OrderedDict(sorted(class_scores.items(),
        key=lambda item: item[1], reverse=True))
      
      return
    
    # don't get top ranked classes or add to scores if scores is empty
    if not scores: return
    
    # default will be equal to score if setdefault inserted a new dictionary item
    # this indicates that scores contains a previous item
    # that we are now ready to find the top scores in
    # here, we use "fancy indexing" in order to get the list of top ranked classes
    if default is score:
      scores = np.mean(scores, axis=0, dtype=np.float32)
      class_indices = scores.argsort()[::-1][:options.top_ranked]
      top_scores[top] = OrderedDict(zip(classes[class_indices].tolist(),
        scores[class_indices], strict=True))
      
      return
    
    # otherwise add the new score, we'll find the mean of them all later
    # (this mutates default)
    default += score
  
  def timestamps(self, shutdown):
    self.predict()
    
    result = {}
    timespan = self.options.timespan
    np = self.np
    top_scores = self._top_scores
    
    class_scores_begin = {}
    class_scores_end = {}
    
    begin = 0
    end = 0
    
    score_begin = 0
    score_end = 0
    
    predictions = list(top_scores.keys())
    predictions_len = len(predictions)
    
    scores = []
    
    for prediction in range(predictions_len + 1):
      if shutdown.is_set(): return None
      
      if prediction != predictions_len:
        score_end = predictions[prediction]
        class_scores_end = top_scores[score_end]
      
      # the first loop iteration is just to initialize scores
      try:
        if scores:
          class_scores_begin = top_scores[score_begin]
          score_begin += timespan
          
          # check if we are still in a contiguous range of timestamps
          # this is where it's important that these were created as OrderedDict
          # as we want to ensure not only that both timestamps have the same classes
          # but also, that they are in the same order
          # these should not compare equal if the keys are in a different order
          if prediction != predictions_len and score_begin == score_end:
            if class_scores_begin.keys() == class_scores_end.keys():
              scores.append(np.fromiter(class_scores_end.values(), dtype=np.float32))
              continue
          
          end = score_begin
          timestamp = self._range_timestamp(begin, end, timespan)
          
          # it is not necessary to sort here again, as it would be impossible
          # for the order to change as the result of averaging here, because
          # we are only joining timestamps where the keys are in the same order
          result[timestamp] = dict(zip(class_scores_begin.keys(),
            np.mean(scores, axis=0, dtype=np.float32).tolist(), strict=True))
      finally:
        score_begin = score_end
      
      # this bit should only be executed if the continue above is not hit
      # scores should start with at least one item in it
      # to work correctly for one-shot sounds not part of a contiguous range
      if prediction != predictions_len:
        begin = score_end
        scores = [np.fromiter(class_scores_end.values(), dtype=np.float32)]
    
    return result
  
  @classmethod
  def restructure_results_for_output(cls, results, output):
    output_timestamps = output.top_ranked_output_timestamps
    
    for file_name_result in results:
      top_scores = file_name_result['result']
      
      if output_timestamps:
        file_name_result['result'] = [{'timestamp': t, 'classes': cs
          } for t, cs in top_scores.items()]
      else:
        file_name_result['result'] = [{'classes': cs
          } for cs in top_scores.values()]
    
    return results
  
  @classmethod
  def print_results_to_output(cls, results, output):
    file = output.file
    model_yamnet_class_names = output.model_yamnet_class_names
    item_delimiter = output.item_delimiter
    indent = output.indent
    output_scores = output.output_scores
    output_timestamps = output.top_ranked_output_timestamps
    
    for file_name_result in results:
      yamosse_output.print_file(file_name_result['file_name'], file=file)
      
      top_scores = file_name_result['result']
      
      try:
        if not top_scores:
          print(indent, None, sep='', file=file)
          continue
        
        # top_scores is a list of dictionaries with 'timestamp' and 'classes' keys
        # it's stored this way for JSON conversion
        # where dictionaries don't preserve their order
        for top_score in top_scores:
          classes = top_score['classes']
          
          # we don't want to sort classes here
          # it should already be sorted as intended by this point
          if output_scores:
            classes = item_delimiter.join(
              [f'{model_yamnet_class_names[c]} ({s:.0%})' for c, s in classes.items()])
          else:
            classes = item_delimiter.join([model_yamnet_class_names[c] for c in classes])
          
          print(indent, end='', file=file)
          
          if output_timestamps:
            print(cls.hms(top_score['timestamp']), end=': ', sep='', file=file)
          
          print(classes, file=file)
      finally:
        print('', file=file)
  
  @classmethod
  def key_number_of_sounds(cls, item):
    return super().key_number_of_sounds((item[1].keys(),))
  
  @classmethod
  def key_result(cls, item):
    begin = super().key_result(item)
    
    try:
      begin, end = begin
    except TypeError:
      return begin, 0
    
    return begin, end


def identification(option=None):
  if option == IDENTIFICATION_CONFIDENCE_SCORE:
    return _IdentificationConfidenceScore
  
  if option == IDENTIFICATION_TOP_RANKED:
    return _IdentificationTopRanked
  
  return _Identification