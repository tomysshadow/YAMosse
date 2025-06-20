try:
  import PyTaskbar
except ImportError:
  PyTaskbar = None

NORMAL = 'normal'
WARNING = 'warning'
ERROR = 'error'
LOADING = 'loading'
DONE = 'done'
RESET = 'reset'

types = {
  NORMAL: None,
  WARNING: None,
  ERROR: None,
  LOADING: None,
  DONE: None,
  RESET: None
}

if PyTaskbar:
  types = {
    NORMAL: PyTaskbar.NORMAL,
    WARNING: PyTaskbar.WARNING,
    ERROR: PyTaskbar.ERROR,
    LOADING: PyTaskbar.LOADING,
    DONE: None,
    RESET: None
  }


def hwnd(window):
  return int(window.wm_frame(), base=16)