from abc import ABC, abstractmethod

import yamosse.utils as yamosse_utils


def identification(option):
  IDENTIFICATION_CONFIDENCE_SCORE = 0
  IDENTIFICATION_TOP_RANKED = 1
  
  TIMESTAMP_ALL = -1
  
  HMS_ALL = 'All'
  HMS_TIMESPAN = ' - '
  
  # general TODO: this whole contraption is in desperate need of unit tests
  class Identification(ABC):
    def __init__(self, options, np):
      self.options = options
      self.np = np
    
    @abstractmethod
    def predict(self, result, prediction_score=None):
      pass
    
    @abstractmethod
    def timestamps(self, result, shutdown):
      pass
    
    @classmethod
    def hms(cls, timestamps):
      # timestamps doesn't need to be a list, just an iterable
      # but we want a list at the end
      keys = []
      
      # this function can operate on either dictionaries or other iterables
      # if operating on a dictionary, it replaces the keys
      # (because the timestamps are always keys)
      try:
        values = timestamps.values()
        timestamps = timestamps.keys()
      except: values = None
      
      for timestamp in timestamps:
        if timestamp == TIMESTAMP_ALL:
          # substitute TIMESTAMP_ALL for HMS_ALL
          timestamp = HMS_ALL
        else:
          # convert to HMS string and join the timestamps if this is a timespan
          try: timestamp = HMS_TIMESPAN.join(yamosse_utils.hours_minutes(t) for t in timestamp)
          except TypeError: timestamp = yamosse_utils.hours_minutes(timestamp)
        
        keys.append(timestamp)
      
      if values is None:
        return keys
      
      return dict(zip(keys, values))
    
    @classmethod
    @abstractmethod
    def print_results_to_output(cls, results, output):
      raise NotImplementedError
    
    @classmethod
    @staticmethod
    def key_result(item):
      # this function is used from Output
      # to sort the column of results that's tabbed in once (one column to the right of file names)
      # that is, classes in Confidence Score mode, or timestamps in Top Ranked mode
      return item[0]
  
  class IdentificationConfidenceScore(Identification):
    def __init__(self, options, *args, **kwargs):
      super().__init__(options, *args, **kwargs)
      
      self._minmax = self._max if options.confidence_score_minmax else self._min
    
    def predict(self, class_predictions, prediction_score=None):
      if not prediction_score: return
      
      prediction, score = prediction_score
      
      options = self.options
      calibration = options.calibration
      confidence_score = options.confidence_score
      
      if options.timespan_span_all: prediction = TIMESTAMP_ALL
      
      # this is pretty self explanatory
      # check if the score we got is above the confidence score
      # if it is, take the max score found per one second of the sound
      # for display if the Output Scores option is checked
      for class_ in options.classes:
        # calibrate the score and ensure it is less than 100%
        calibrated_score = min(score[class_] * calibration[class_], 1.0)
        if not self._minmax(calibrated_score, confidence_score): continue
        
        prediction_scores = class_predictions.setdefault(class_, {})
        
        prediction_scores[prediction] = max(
          prediction_scores.get(prediction, calibrated_score), calibrated_score)
    
    def timestamps(self, class_predictions, shutdown):
      # create timestamps from predictions/scores
      results = {}
      
      options = self.options
      timespan = options.timespan
      
      for class_, prediction_scores in class_predictions.items():
        if shutdown.is_set(): return None
        
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
            timestamp = (begin, end) if timespan and begin + timespan < end else begin
            timestamp_scores[timestamp] = float(max(scores[score_begin:score_end + 1]))
            
            score_begin = prediction_end
          
          score_end = prediction_end
        
        # class is cast to int for same reason as above (it might come from a numpy array)
        results[int(class_)] = timestamp_scores
      
      return results
    
    @classmethod
    def hms(cls, results):
      # super call is done out here to avoid the overhead of doing it every loop
      identification = super()
      
      for file_name, class_timestamps in results.items():
        for class_, timestamps in class_timestamps.items():
          timestamps = identification.hms(timestamps)
          
          # if Output Scores is checked, timestamps will be a dictionary
          # for JSON that won't preserve insertion order, so we need to make it a list
          try: timestamps = timestamps.items()
          except: pass
          else: timestamps = [{'timestamp': ts, 'score': s} for ts, s in timestamps]
          
          class_timestamps[class_] = timestamps
      
      return results
    
    @classmethod
    def print_results_to_output(cls, results, output):
      file = output.file
      model_yamnet_class_names = output.model_yamnet_class_names
      item_delimiter = output.item_delimiter
      output_scores = output.output_scores
      
      for file_name, class_timestamps in results.items():
        output.print_file(file_name)
        
        # this try-finally is just to ensure the newline is always printed even when continuing
        try:
          # if no timestamps were found for this file, then print None for this file
          if not class_timestamps:
            print('\t', None, sep='', file=file)
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
                if timestamp_score['timestamp'] == HMS_ALL:
                  all_timestamp = (class_name, timestamps.pop(t))
                  break
            else:
              try: timestamps.remove(HMS_ALL)
              except ValueError: pass
              else: all_timestamp = class_name
            
            if not all_timestamp is None:
              assert not timestamps, 'timestamps must be empty if Span All is checked'
              
              all_timestamps.append(all_timestamp)
              continue
            
            if output_scores:
              timestamps = [f'{t["timestamp"]} ({t["score"]:.0%})' for t in timestamps]
            
            print('\t', class_name, ':\n\t\t',
              item_delimiter.join(timestamps), sep='', file=file)
          
          if all_timestamps:
            # in this case we want to print the class names and scores, but not timestamps
            if output_scores:
              all_timestamps = [f'{c} ({t["score"]:.0%})' for c, t in all_timestamps]
            
            print('\t', item_delimiter.join(all_timestamps), sep='', file=file)
        finally:
          print('', file=file)
    
    @staticmethod
    def _min(calibrated_score, confidence_score):
      return calibrated_score >= confidence_score
    
    @staticmethod
    def _max(calibrated_score, confidence_score):
      return calibrated_score < confidence_score
      
  
  class IdentificationTopRanked(Identification):
    def __init__(self, options, np):
      super().__init__(options, np)
      
      self.calibration = np.take(options.calibration, options.classes)
    
    def predict(self, top_scores, prediction_score=None):
      np = self.np
      
      options = self.options
      classes = options.classes
      
      # top should be zero (not None) by default
      # this is what ensures the timer starts at zero
      top = 0
      scores = []
      
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
        score = np.minimum(score.take(classes) * self.calibration, 1.0)
        
        # in the span all case, we actually just want to list
        # every class that is ever in the top ranked as one big summary
        # so we don't bother with the whole numpy stacking thing
        # we also don't care about timestamps in this case
        # so the None key is used exclusively
        if options.timespan_span_all:
          class_scores = top_scores.setdefault(TIMESTAMP_ALL, {})
          class_indices = score.argsort()[::-1][:options.top_ranked]
          
          # here we need to go back to storing this as a stock Python list
          # as we need to expand it with new scores, so a numpy array wouldn't cut it
          # (or at least, wouldn't be efficient with all the copying of arrays)
          for class_index in class_indices:
            scores = class_scores.setdefault(int(classes[class_index]), [])
            scores += [score[class_index]]
          
          return
        
        timespan = options.timespan
        
        # when timespan is zero, prediction should always be set to its initial value
        # this tells the location of the first sound identified, which is useful information
        if timespan: prediction = prediction // timespan * timespan
        elif top_scores: prediction = top
        
        score = [score]
        default = top_scores.setdefault(int(prediction), score)
      elif options.timespan_span_all:
        # this only happens on the last call, from the timestamps method
        # (when prediction_score is None)
        # we use this opportunity to convert top_scores into its final form
        # specifically, to find averages for all of the scores for each class
        class_scores = top_scores[TIMESTAMP_ALL]
        
        for class_, scores in class_scores.items():
          class_scores[class_] = float(np.mean(scores, axis=0))
        
        # normally numpy's argsort function handles the sorting directly on the arrays
        # but now we've averaged the scores so it's all outta whack
        # so we gotta sort it now again
        # just using the stock Python functions this time, because now this is a dictionary
        top_scores[TIMESTAMP_ALL] = yamosse_utils.dict_sorted(class_scores,
          key=lambda item: item[1], reverse=True)
        
        return
      
      # don't get top ranked classes or add to scores if scores is empty
      if not scores: return
      
      # default will be equal to score if setdefault inserted a new dictionary item
      # this indicates that scores contains a previous item
      # that we are now ready to find the top scores in
      # here, we use "fancy indexing" in order to get the list of top ranked classes
      if default is score:
        scores = np.mean(scores, axis=0)
        class_indices = scores.argsort()[::-1][:options.top_ranked]
        top_scores[top] = dict(zip(classes[class_indices].tolist(),
          scores[class_indices].tolist()))
        
        return
      
      # otherwise add the new score, we'll find the mean of them all later
      default += score
    
    def timestamps(self, top_scores, shutdown):
      self.predict(top_scores)
      return top_scores
    
    @classmethod
    def hms(cls, results):
      # super call must be done out here because it doesn't work in list comprehensions
      identification = super()
      
      for file_name, top_scores in results.items():
        results[file_name] = [{'timestamp': t, 'classes': cs} for t, cs in identification.hms(
          top_scores).items()]
      
      return results
    
    @classmethod
    def print_results_to_output(cls, results, output):
      file = output.file
      model_yamnet_class_names = output.model_yamnet_class_names
      item_delimiter = output.item_delimiter
      output_scores = output.output_scores
      output_timestamps = output.top_ranked_output_timestamps
      
      for file_name, top_scores in results.items():
        output.print_file(file_name)
        
        # top_scores is a list of dictionaries with 'timestamp' and 'classes' keys
        # (it's stored this way for JSON conversion where dictionaries don't preserve their order)
        for top_score in top_scores:
          classes = top_score['classes']
          
          # we don't want to sort classes here
          # it should already be sorted as intended by this point
          if output_scores:
            classes = item_delimiter.join(
              [f'{model_yamnet_class_names[c]} ({s:.0%})' for c, s in classes.items()])
          else:
            classes = item_delimiter.join([model_yamnet_class_names[c] for c in classes])
          
          print('\t', end='', file=file)
          
          if output_timestamps:
            print(top_score['timestamp'], end=': ', sep='', file=file)
          
          print(classes, file=file)
        
        print('', file=file)
  
  if option == IDENTIFICATION_CONFIDENCE_SCORE:
    return IdentificationConfidenceScore
  elif option == IDENTIFICATION_TOP_RANKED:
    return IdentificationTopRanked
  
  return Identification