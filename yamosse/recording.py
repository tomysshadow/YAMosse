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
MILLISECONDS = 100
LINE = '#' * 80

def input_devices():
  input_default = sd.default.device[0]
  
  hostapis = sd.query_hostapis()
  devices = sd.query_devices()
  
  names = ['%s%s - %s' % ('> ' if d['index'] == input_default else '', d['name'],
    hostapis[d['hostapi']]['name']) for d in devices]
  
  return (
    {names[index := d['index']]: index for d in devices if d['max_input_channels']},
    names[input_default]
  )

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
          blocksize=yamosse_worker.SAMPLE_RATE // (1000 // MILLISECONDS),
          callback=lambda indata, *args, **kwargs: indatas.put(indata.copy())
        )
      ):
        print(LINE, 'press Ctrl+C to stop the recording', LINE, sep='\n')
        
        try:
          while not stop.is_set():
            indata = indatas.get()
            if indata.size: self.volume = float(options.loglinear(np, np.abs(indata.max())))
            f.write(indata)
        except KeyboardInterrupt:
          pass
    except:
      save = False
      raise
    finally:
      tmp.close()
      
      if not save or not self.save:
        unlink(tmp.name)
    
    print('')
    print(f'Recording finished: {tmp.name!r}')
    
    subsystem.variables_to_object(options)
    input_ = shlex.join(shlex.split(options.input) + [tmp.name])
    options.input = input_
    subsystem.set_variable_after_idle('input', input_)