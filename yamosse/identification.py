from abc import ABC, abstractmethod

import yamosse.utils as yamosse_utils


def identification(option):
  IDENTIFICATION_CONFIDENCE_SCORE = 0
  IDENTIFICATION_TOP_RANKED = 1
  
  COMBINE_ALL_KEY = -1
  
  # general TODO: this whole contraption is in desperate need of unit tests
  class Identification(ABC):
    def __init__(self, options, np):
      self.options = options
      self.np = np
    
    @abstractmethod
    def predict(self, identified, prediction_score=None):
      pass
    
    @abstractmethod
    def timestamps(self, identified, shutdown):
      pass
    
    @classmethod
    @abstractmethod
    def print_results_to_output(results, output):
      raise NotImplementedError
    
    @classmethod
    @staticmethod
    def key_identified(item):
      return item[0] # TODO
  
  class IdentificationConfidenceScore(Identification):
    def predict(self, class_predictions, prediction_score=None):
      if not prediction_score: return
      
      prediction, score = prediction_score
      
      options = self.options
      calibration = options.calibration
      confidence_score = options.confidence_score
      
      # this is pretty self explanatory
      # check if the score we got is above the confidence score
      # if it is, take the max score found per one second of the sound
      # for display if the Output Scores option is checked
      for class_ in options.classes:
        # TODO: min/max
        calibrated_score = score[class_] * calibration[class_]
        if calibrated_score < confidence_score: continue
        
        prediction_scores = class_predictions.setdefault(class_, {})
        
        prediction_scores[prediction] = max(
          prediction_scores.get(prediction, calibrated_score), calibrated_score)
    
    def timestamps(self, class_predictions, shutdown):
      # create timestamps from predictions/scores
      results = {}
      
      options = self.options
      combine = options.combine
      
      if options.combine_all:
        results[COMBINE_ALL_KEY] = {}
      
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
            timestamp = (begin, end) if combine and begin + combine < end else begin
            timestamp_scores[timestamp] = float(max(scores[score_begin:score_end + 1]))
            
            score_begin = prediction_end
          
          score_end = prediction_end
        
        # class is cast to int for same reason as above (it might come from a numpy array)
        results[int(class_)] = timestamp_scores
      
      return results
    
    # TODO: this has to be decoupled from printing
    # we need to make this work with JSON somehow
    @classmethod
    def print_results_to_output(cls, results, output):
      file = output.file
      model_yamnet_class_names = output.model_yamnet_class_names
      item_delimiter = output.item_delimiter
      output_scores = output.output_scores
      
      for file_name, class_timestamps in results.items():
        output.print_file(file_name)
      
        combine_all = not class_timestamps.pop(COMBINE_ALL_KEY, True)
        
        # this try-finally is just to ensure the newline is always printed even when continuing
        try:
          # if no timestamps were found for this file, then print None for this file
          if not class_timestamps:
            print('\t', None, sep='', file=file)
            continue
          
          # if we're combining all we don't care about the timestamps
          # (but they're still in the data structure for sorting consistency)
          if combine_all:
            if output_scores:
              class_timestamps = [f'{model_yamnet_class_names[c]} ({max(ts.values()):.0%})' for c, ts in class_timestamps.items()]
            else:
              class_timestamps = [model_yamnet_class_names[c] for c in class_timestamps.keys()]
            
            print('\t', item_delimiter.join(class_timestamps), sep='', file=file)
            continue
          
          for class_, timestamp_scores in class_timestamps.items():
            # timestamp_scores will be a list if Output Scores is off
            if output_scores:
              timestamp_scores = [f'{cls._hms(t)} ({s:.0%})' for t, s in timestamp_scores.items()]
            else:
              timestamp_scores = [cls._hms(t) for t in timestamp_scores]
            
            print('\t', model_yamnet_class_names[class_], ':\n\t\t',
              item_delimiter.join(timestamp_scores), sep='', file=file)
          
        finally:
          print('', file=file)
    
    @classmethod
    @staticmethod
    def _hms(timestamp):
      try: return ' - '.join(yamosse_utils.hours_minutes(t) for t in timestamp)
      except TypeError: return yamosse_utils.hours_minutes(timestamp)
  
  class IdentificationTopRanked(Identification):
    def __init__(self, options, np):
      super().__init__(options, np)
      
      self.calibration = np.take(options.calibration, options.classes)
    
    def predict(self, top_scores, prediction_score=None):
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
      # round down predictions to nearest "combine" range
      # we also only take the scores we specifically care about (saves memory)
      # we will be able to get them back later by indexing into the classes array
      if prediction_score:
        prediction, score = prediction_score
        score = score.take(classes) * self.calibration
        
        # in the combine all case, we actually just want to list
        # every class that is ever in the top ranked as one big summary
        # so we don't bother with the whole numpy stacking thing
        # we also don't care about timestamps in this case
        # so the None key is used exclusively
        if options.combine_all:
          class_scores = top_scores.setdefault(COMBINE_ALL_KEY, {})
          class_indices = score.argsort()[::-1][:options.top_ranked]
          
          # here we need to go back to storing this as a stock Python list
          # as we need to expand it with new scores, so a numpy array wouldn't cut it
          # (or at least, wouldn't be efficient with all the copying of arrays)
          for class_index in class_indices:
            scores = class_scores.setdefault(int(classes[class_index]), [])
            scores += [score[class_index]]
          
          return
        
        # when combine is zero, prediction should always be set to its initial value
        # this tells the location of the first sound identified, which is useful information
        combine = options.combine
        
        if combine: prediction = prediction // combine * combine
        elif top_scores: prediction = top
        
        score = [score]
        default = top_scores.setdefault(int(prediction), score)
      elif options.combine_all:
        # this only happens on the last call, from the timestamps method
        # (when prediction_score is None)
        # we use this opportunity to convert top_scores into its final form
        # specifically, to find averages for all of the scores for each class
        class_scores = top_scores[COMBINE_ALL_KEY]
        
        for class_, scores in class_scores.items():
          class_scores[class_] = float(self.np.mean(scores, axis=0))
        
        # normally numpy's argsort function handles the sorting directly on the arrays
        # but now we've averaged the scores so it's all outta whack
        # so we gotta sort it now again
        # just using the stock Python functions this time, because now this is a dictionary
        top_scores[COMBINE_ALL_KEY] = yamosse_utils.dict_sorted(class_scores,
          key=lambda item: item[1], reverse=True)
        
        return
      
      # don't get top ranked classes or add to scores if scores is empty
      if not scores: return
      
      # default will be equal to score if setdefault inserted a new dictionary item
      # this indicates that scores contains a previous item
      # that we are now ready to find the top scores in
      # here, we use "fancy indexing" in order to get the list of top ranked classes
      if default is score:
        scores = self.np.stack(scores).mean(axis=0)
        class_indices = scores.argsort()[::-1][:options.top_ranked]
        top_scores[top] = dict(zip(classes[class_indices].tolist(),
          scores[class_indices].tolist()))
        
        return
      
      # otherwise add the new score, to be stacked in a later call
      default += score
    
    def timestamps(self, top_scores, shutdown):
      self.predict(top_scores)
      
      # the presence of the None key is what determines if timestamps are output
      # yes, this is a kludge - but we need to pickle out this information somehow
      # plus we're basically already relying on this being true for Combine All to work anyway
      # here, we are taking advantage of the fact that Top Ranked must be at least one
      # (so an empty dictionary can be disregarded)
      # the value can't be None! Otherwise sorting the top scores by their lengths could fail
      if not self.options.top_ranked_output_timestamps:
        results.setdefault(COMBINE_ALL_KEY, {})
      
      return results
    
    @classmethod
    def print_results_to_output(cls, results, output):
      file = output.file
      model_yamnet_class_names = output.model_yamnet_class_names
      item_delimiter = output.item_delimiter
      output_scores = output.output_scores
      
      for file_name, top_scores in results.items():
        output.print_file(file_name)
        
        output_timestamps = not COMBINE_ALL_KEY in top_scores
        
        for timestamp, class_scores in top_scores.items():
          # number of Top Ranked items must be at least one
          # if it's an empty dictionary we disregard it and continue
          # (this facilitates the Output Timestamps option)
          if output_timestamps:
            print('\t', output.hours_minutes(timestamp), end=': ', sep='', file=file)
          elif class_scores:
            print('\t', end='', file=file)
          else: continue
          
          # we don't want to sort class_scores here
          # it should already be sorted as intended by this point
          if output_scores:
            class_scores = item_delimiter.join(
              [f'{model_yamnet_class_names[c]} ({s:.0%})' for c, s in class_scores.items()])
          else:
            class_scores = item_delimiter.join(
              [model_yamnet_class_names[c] for c in class_scores])
          
          print(class_scores, file=file)
        
        print('', file=file)
    
    @classmethod
    @staticmethod
    def key_identified(item):
      return False
  
  if option == IDENTIFICATION_CONFIDENCE_SCORE:
    return IdentificationConfidenceScore
  elif option == IDENTIFICATION_TOP_RANKED:
    return IdentificationTopRanked
  
  return Identification