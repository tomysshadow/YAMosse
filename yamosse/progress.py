from enum import Enum

try:
  import PyTaskbar
except ImportError:
  PyTaskbar = None


class Function(Enum):
  DONE = 'done'
  RESET = 'reset'


class State(Enum):
  NORMAL = ('', 1)
  ERROR = ('user1', 2)
  PAUSED = ('user2', 3)
  PARTIAL = ('user3', 4)
  
  def on(self):
    return self.value[0]
  
  def off(self):
    statespec = self.value[0]
    
    if not statespec:
      return ''
    
    return '!%s' % statespec


class Mode(Enum):
  DETERMINATE = 'determinate'
  INDETERMINATE = 'indeterminate'


class Progress:
  __slots__ = ('_step', '_steps', '_sender', '_current_step')
  
  MAXIMUM = 100
  
  def __init__(self, step, steps, sender):
    self._step = step
    self._steps = self.MAXIMUM * steps
    self._sender = sender
    
    self._current_step = 0
  
  def __enter__(self):
    self._current_step = 0
    return self
  
  def __exit__(self, exc, val, tb):
    self.step()
  
  def step(self, current_step=1.0):
    MAXIMUM = self.MAXIMUM
    
    current_step = int(MAXIMUM * current_step) - self._current_step
    
    if current_step <= 0:
      return
    
    previous_step = 0
    self._current_step += current_step
    next_step = 0
    
    step = self._step
    
    with step.get_lock():
      previous_step = step.value
      step.value += current_step
      next_step = step.value
    
    steps = MAXIMUM / self._steps
    
    previous_progress = int(previous_step * steps) + 1
    next_progress = int(next_step * steps) + 1
    
    sender = self._sender
    
    for current_progress in range(previous_progress, next_progress):
      sender.send({
        'progressbar': {
          'set': {'args': (current_progress,)}
        },
        
        'log': '%d%% complete' % current_progress
      })


def hwnd(window):
  return int(window.frame(), base=16)


if PyTaskbar:
  types = {
    Function.DONE: 'flash_done',
    Function.RESET: 'reset',
    
    State.NORMAL: PyTaskbar.NORMAL,
    State.ERROR: PyTaskbar.ERROR,
    State.PAUSED: PyTaskbar.WARNING,
    State.PARTIAL: None,
    
    Mode.DETERMINATE: None,
    Mode.INDETERMINATE: PyTaskbar.LOADING
  }
else:
  types = dict.fromkeys((
    *Function,
    *State,
    *Mode
  ))