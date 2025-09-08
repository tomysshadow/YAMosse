from os import mkdir
from shlex import quote
from threading import Lock, Event
from queue import Queue
from contextlib import suppress

import soundfile as sf
import sounddevice as sd

import yamosse.worker as yamosse_worker
import yamosse.hiddenfile as yamosse_hiddenfile


class Recording:
  PREFIX = 'Recording_'
  SUFFIX = '.wav'
  DIR = 'My Recordings'
  
  BLOCKSIZE_SECONDS = 0.1
  
  LINE = '#' * 80
  
  VOLUME_NAME = 'Volume:'
  VOLUME_SPEC = '{volume:>4.0%}'
  
  RECORDING_ABORTED_SPEC = 'Recording aborted: {message}'
  RECORDING_FINISHED_SPEC = 'Recording finished: {input}'
  
  NO_INPUT_DEVICES_MESSAGE = RECORDING_ABORTED_SPEC.format(
    message='there are no input devices.')
  
  NO_SAVE_MESSAGE = RECORDING_ABORTED_SPEC.format(
    message='the user did not save the recording.')
  
  def __init__(self, subsystem, options, start=None, stop=None):
    self.save = True
    self.options = options
    
    self._start = Lock() if start is None else start
    self._stop = Event() if stop is None else stop
    
    self._volume = 0.0
    
    subsystem.start(self._thread)
  
  def _thread(self):
    import numpy as np # Make sure NumPy is loaded before it is used in the callback
    
    with self._start:
      options = self.options
      input_devices, input_default_name = self.input_devices()
      
      input_device = options.input_device
      
      try:
        device = input_devices[input_device]
      except KeyError:
        try:
          device = input_devices[input_device := input_default_name]
        except KeyError:
          print(self.NO_INPUT_DEVICES_MESSAGE)
          return
        
        options.input_device = input_device
      
      VOLUME_SPEC = self.VOLUME_SPEC
      
      volume = 0.0
      volume_str = VOLUME_SPEC.format(volume=volume)
      volume_backspaces = '\b' * len(volume_str)
      
      indatas = Queue()
      
      # try and ensure the directory exists
      with suppress(FileExistsError):
        mkdir(self.DIR)
      
      # we don't need to use a with statement for hidden
      # it's designed such that it will free when it goes out of scope
      hidden = yamosse_hiddenfile.HiddenFile(
        mode='wb',
        prefix=self.PREFIX, suffix=self.SUFFIX, dir=self.DIR
      )
      
      # Make sure the file is opened before recording anything:
      with (
        sf.SoundFile(
          hidden, mode='x',
          samplerate=yamosse_worker.SAMPLE_RATE, channels=yamosse_worker.MONO
        ) as f,
        
        sd.InputStream(
          device=device,
          samplerate=yamosse_worker.SAMPLE_RATE, channels=yamosse_worker.MONO,
          blocksize=int(yamosse_worker.SAMPLE_RATE * self.BLOCKSIZE_SECONDS),
          callback=lambda indata, frames, time, status: indatas.put(indata.copy())
        )
      ):
        try:
          LINE = self.LINE
          
          print(LINE, 'press Ctrl+C to stop the recording', LINE, sep='\n', end='\n\n')
          print(self.VOLUME_NAME, volume_str, end='', flush=True)
          
          stop = self._stop
          indata = None
          
          while not stop.is_set():
            self._volume = volume
            
            print(volume_backspaces, VOLUME_SPEC.format(volume=volume),
              sep='', end='', flush=True)
            
            queued = True
            
            while queued:
              # this is done first so we block
              indata = indatas.get()
              f.write(indata)
              
              # ensure we get all input data if there are multiple queued things piled up
              queued = not indatas.empty()
            
            # only after we've definitely written something, set the new volume
            volume = float(options.volume_loglinear(np, np.abs(indata).max()))
        except KeyboardInterrupt:
          pass
        finally:
          # this is in the finally block so that
          # there will always be a newline after the volume
          # even in the exception case
          print(volume_backspaces, volume_str, sep='', flush=True)
      
      # this should only be saved if no exception occurred
      # done outside with statement so it's closed
      # after SoundDevice is done using it
      hidden.save = self.save
      hidden.close()
      
      input_ = hidden.name
      print('')
      
      if not input_:
        print(self.NO_SAVE_MESSAGE)
        return
      
      input_ = quote(input_)
      print(self.RECORDING_FINISHED_SPEC.format(input=input_), sep='', end='\n\n')
      
      # a previous iteration of this appended the name instead of replacing it
      # but it was broken because the input field can contain folder names
      # in which case, there is only supposed to be one
      # so now we just replace it
      options.input = input_
  
  def volume(self):
    return self._volume
  
  @classmethod
  @staticmethod
  def input_devices():
    input_default = sd.default.device[0]
    
    hostapis = sd.query_hostapis()
    devices = sd.query_devices()
    
    # by inserting an indicator for the default input device
    # it will cause the option to automatically change if the default changes
    # and the option was previously set to the default
    names = ['%s%s - %s' % ('> ' if d['index'] == input_default else '', d['name'],
      hostapis[d['hostapi']]['name']) for d in devices]
    
    try:
      input_default_name = names[input_default]
    except IndexError:
      input_default_name = ''
    
    return (
      {names[index := d['index']]: index for d in devices if d['max_input_channels']},
      input_default_name
    )