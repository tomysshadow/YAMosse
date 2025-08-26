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
  'user3',
  'user2',
  'user1',
  ''
)

STATE_PARTIAL, STATE_PAUSED, STATE_ERROR, STATE_NORMAL = STATES

MODES = (
  'determinate',
  'indeterminate'
)

MODE_DETERMINATE, MODE_INDETERMINATE = MODES

types = dict.fromkeys((*COMMANDS, *STATES, *MODES))

if PyTaskbar:
  types = {
    COMMAND_DONE: 'flash_done',
    COMMAND_RESET: 'reset',
    
    STATE_PARTIAL: None,
    STATE_PAUSED: PyTaskbar.WARNING,
    STATE_ERROR: PyTaskbar.ERROR,
    STATE_NORMAL: PyTaskbar.NORMAL,
    
    MODE_DETERMINATE: None,
    MODE_INDETERMINATE: PyTaskbar.LOADING
  }


def not_state(state):
  return '!%s' % state


def hwnd(window):
  return int(window.wm_frame(), base=16)