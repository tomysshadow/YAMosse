from enum import Enum

try:
  import PyTaskbar
except ImportError:
  PyTaskbar = None


class Function(Enum):
  DONE = 'done'
  RESET = 'reset'


class State(Enum):
  # order matters for priority levels
  PARTIAL = (4, 'user3')
  PAUSED = (3, 'user2')
  ERROR = (2, 'user1')
  NORMAL = (1, '')
  
  def on(self):
    return self.value[1]
  
  def off(self):
    value = self.value[1]
    
    if not value:
      return ''
    
    return '!%s' % value


class Mode(Enum):
  DETERMINATE = 'determinate'
  INDETERMINATE = 'indeterminate'


def hwnd(window):
  return int(window.wm_frame(), base=16)


types = dict.fromkeys((*Function, *State, *Mode))

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