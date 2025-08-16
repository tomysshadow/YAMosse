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
LINE = '#' * 80


def record(subsystem, options, stop=None, device=None):
  import numpy # Make sure NumPy is loaded before it is used in the callback
  assert numpy # avoid "imported but unused" message (W0611)
  
  if stop is None: stop = Event()
  if device is None: device = sd.default.device[0]
  
  indatas = Queue()
  
  # Make sure the file is opened before recording anything:
  with (
    NamedTemporaryFile(
      delete=False, mode='wb',
      prefix=PREFIX, suffix=SUFFIX, dir=DIR
    ) as tmp,
    
    sf.SoundFile(
      tmp, mode='x',
      samplerate=yamosse_worker.SAMPLE_RATE, channels=yamosse_worker.MONO
    ) as f,
    
    sd.InputStream(
      device=device,
      samplerate=yamosse_worker.SAMPLE_RATE, channels=yamosse_worker.MONO,
      callback=lambda indata, *args, **kwargs: indatas.put(indata.copy())
    )
  ):
    name = tmp.name
    print(LINE, 'press Ctrl+C to stop the recording', LINE, sep='\n')
    
    try:
      while not stop.is_set(): f.write(indatas.get())
    except KeyboardInterrupt:
      pass
    
    stop.clear()
    
    subsystem.variables_to_object(options)
    input_ = shlex.join(shlex.split(options.input) + [name])
    options.input = input_
    subsystem.set_variable_after_idle('input', input_)
    
    print('')
    print(f'Recording finished: {name!r}')