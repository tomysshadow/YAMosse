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


def hwnd(window):
  return int(window.wm_frame(), base=16)


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