from os import unlink
import shlex
from threading import Event
from tempfile import NamedTemporaryFile
from queue import Queue

import soundfile as sf
import sounddevice as sd

import yamosse.worker as yamosse_worker

PREFIX = 'Recording_'
SUFFIX = '.wav'
DIR = 'My Recordings'

BLOCKSIZE_SECONDS = 0.1

LINE = '#' * 80

class Recording:
  def __init__(self):
    self.save = True
    self.volume = 0.0
  
  def thread(self, subsystem, options, stop=None, device=None):
    import numpy as np # Make sure NumPy is loaded before it is used in the callback
    
    if stop is None: stop = Event()
    if device is None: device = sd.default.device[0]
    
    save = True
    indatas = Queue()
    
    # Make sure the file is opened before recording anything:
    tmp = NamedTemporaryFile(
      delete=False, mode='wb',
      prefix=PREFIX, suffix=SUFFIX, dir=DIR
    )
    
    try:
      with (
        sf.SoundFile(
          tmp, mode='x',
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
          print(LINE, 'press Ctrl+C to stop the recording', LINE, sep='\n')
          
          indata = None
          
          while not stop.is_set():
            queued = True
            
            while queued:
              # this is done first so we block
              indata = indatas.get()
              f.write(indata)
              
              # ensure we get all input data if there are multiple queued things piled up
              queued = not indatas.empty()
            
            # only after we've definitely written something, set the new volume
            self.volume = float(options.loglinear(np, np.abs(indata).max()))
        except KeyboardInterrupt:
          pass
    except:
      # this must be a distinct variable to self.save because
      # otherwise it might get set back to true by some other thread
      # before it is used
      save = False
      raise
    finally:
      tmp.close()
      
      # delete the file if the user opted not to save it
      # or an exception occurred
      save &= self.save
      if not save: unlink(tmp.name)
    
    # this can't happen in the finally block
    # because it might silence an exception
    if not save: return
    
    name = tmp.name
    
    print('')
    print(f'Recording finished: {name!r}')
    
    subsystem.variables_to_object(options)
    input_ = shlex.join(shlex.split(options.input) + [name])
    options.input = input_
    subsystem.set_variable_after_idle('input', input_)


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