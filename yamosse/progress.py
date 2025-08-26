try:
  import PyTaskbar
except ImportError:
  PyTaskbar = None

COMMANDS = (
  'done',
  'reset'
)

COMMAND_DONE, COMMAND_RESET = COMMANDS

STATES = (
  '', # normal
  'user1', # error
  'user2', # paused
  'user3' # partial
)

STATE_NORMAL, STATE_ERROR, STATE_WARNING, STATE_PARTIAL = STATES

MODES = (
  'determinate',
  'indeterminate'
)

MODE_NORMAL, MODE_LOADING = MODES

types = dict.fromkeys((*COMMANDS, *STATES, *MODES))

if PyTaskbar:
  types = {
    COMMAND_DONE: 'flash_done',
    COMMAND_RESET: 'reset',
    
    STATE_NORMAL: PyTaskbar.NORMAL,
    STATE_ERROR: PyTaskbar.ERROR,
    STATE_WARNING: PyTaskbar.WARNING,
    STATE_PARTIAL: None,
    
    MODE_NORMAL: None,
    MODE_LOADING: PyTaskbar.LOADING
  }


def disabled_state(state):
  return '!%s' % state


def hwnd(window):
  return int(window.wm_frame(), base=16)