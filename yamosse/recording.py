from os import mkdir, unlink
from shlex import quote
from threading import Lock, Event
from queue import Queue

import soundfile as sf
import sounddevice as sd

import yamosse.worker as yamosse_worker
import yamosse.hiddenfile as yamosse_hiddenfile

PREFIX = 'Recording_'
SUFFIX = '.wav'
DIR = 'My Recordings'

BLOCKSIZE_SECONDS = 0.1

LINE = '#' * 80
VOLUME_SPEC = '{volume:>4.0%}'


class Recording:
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
      input_devices, input_default_name = Recording.input_devices()
      
      input_device = options.input_device
      
      try:
        device = input_devices[input_device]
      except KeyError:
        device = input_devices[input_device := input_default_name]
        
        options.input_device = input_device
      
      volume = 0.0
      volume_str = VOLUME_SPEC.format(volume=volume)
      volume_backspaces = '\b' * len(volume_str)
      
      name = None
      indatas = Queue()
      
      # try and ensure the directory exists
      try:
        mkdir(DIR)
      except FileExistsError:
        pass
      
      # Make sure the file is opened before recording anything:
      with (
        yamosse_hiddenfile.HiddenFile(
          mode='wb',
          prefix=PREFIX, suffix=SUFFIX, dir=DIR
        ) as hidden,
        
        sf.SoundFile(
          hidden, mode='x',
          samplerate=yamosse_worker.SAMPLE_RATE, channels=yamosse_worker.MONO
        ) as f,
        
        sd.InputStream(
          device=device,
          samplerate=yamosse_worker.SAMPLE_RATE, channels=yamosse_worker.MONO,
          blocksize=int(yamosse_worker.SAMPLE_RATE * BLOCKSIZE_SECONDS),
          callback=lambda indata, *args, **kwargs: indatas.put(indata.copy())
        )
      ):
        try:
          print(LINE, 'press Ctrl+C to stop the recording', LINE, sep='\n', end='\n\n')
          print('Volume:', volume_str, end='', flush=True)
          
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
        else:
          # we shouldn't save if an exception occured
          # if we were successful, we save if self.save is True
          # (meaning user hit Yes to ask save box)
          if not self.save: return
          
          name = hidden.visible_name
          hidden.save_name = name
        finally:
          # this is in the finally block so that
          # there will always be a newline after the volume
          # even in the exception case
          print(volume_backspaces, volume_str, sep='', flush=True)
      
      input_ = quote(name)
      print('\nRecording finished:', input_, end='\n\n')
      
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
    
    return (
      {names[index := d['index']]: index for d in devices if d['max_input_channels']},
      names[input_default]
    )