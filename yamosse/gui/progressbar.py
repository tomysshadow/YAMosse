import tkinter as tk
from tkinter import ttk

import yamosse.progress as yamosse_progress
import yamosse.utils as yamosse_utils

from .. import gui

COMMAND_RESET_STATES = ['!%s' % s for s in yamosse_progress.STATES if s]


class Progressbar(ttk.Progressbar):
  def __init__(self, frame, name='', variable=None,
  mode=yamosse_progress.MODE_NORMAL, parent=None, task=False, **kwargs):
    frame.rowconfigure(0, weight=1) # make progressbar vertically centered
    frame.columnconfigure(1, weight=1) # make progressbar horizontally resizable
    
    self._state_type = yamosse_progress.types[yamosse_progress.STATE_NORMAL]
    self._variable = None
    self._cbname = ''
    self._value = 0
    
    self.name = gui.make_name(frame, name)
    
    taskbar = None
    
    if task and yamosse_progress.PyTaskbar:
      if not parent:
        parent = frame.winfo_toplevel()
      
      taskbar = yamosse_progress.PyTaskbar.Progress(
        hwnd=yamosse_progress.hwnd(parent)
      )
    
    self.taskbar = taskbar
    
    self.percent = gui.make_percent(frame)
    
    super().__init__(frame, variable=variable, **kwargs)
    super().grid(row=0, column=1, sticky=tk.EW)
    
    self.variable = variable
    self.mode = mode
  
  def configure(self, cnf={}, **kw):
    kw = cnf | kw
    kw_len = len(kw)
    
    if kw_len == 0: # return all options
      return super().configure()
    
    if kw_len == 1 and next(iter(kw.values())) is None: # return argument values
      return super().configure(**kw)
    
    try:
      self.variable = kw['variable']
    except KeyError:
      pass
    
    try:
      self.mode = kw['mode']
    except KeyError:
      pass
    
    return super().configure(**kw)
  
  def value(self, value):
    if value in yamosse_progress.COMMANDS:
      return self.command(value)
    
    try:
      state = yamosse_utils.intersects([str(v) for v in value], yamosse_progress.STATES)
    except ValueError:
      pass
    else:
      if state:
        return self.state(value)
    
    if value in yamosse_progress.MODES:
      return self.mode(value)
    
    self.variable.set(value)
  
  def command(self, command):
    if command not in yamosse_progress.COMMANDS:
      raise ValueError('command must be in %r' % (yamosse_progress.COMMANDS,))
    
    if command == yamosse_progress.COMMANDS_DONE:
      self.mode(mode=yamosse_progress.MODE_NORMAL)
      self._setvar(int(self['maximum']))
      
      # the taskbar may only flash in the normal state
      # because it also resets the progress type
      # so it would become out of sync with the progress bar otherwise
      if super().state():
        return
    elif command == yamosse_progress.COMMANDS_RESET:
      self.state(COMMAND_RESET_STATES)
      self._setvar(0)
    
    self._command_taskbar(command)
  
  def state(self, statespec=None):
    result = super().state(statespec=statespec)
    
    # we only need to do stuff when setting the state
    if statespec is None:
      return result
    
    # reversed so that highest priority states are tried first
    for state in reversed(yamosse_progress.STATES):
      if not super().instate(state):
        continue
      
      state_type = yamosse_progress.types[state]
      
      if state_type is not None:
        self._state_type = state_type
        break
    
    self._mode_state_taskbar()
    return result
  
  @property
  def mode(self):
    return self['mode']
  
  @property.setter
  def mode(self, value):
    if value == yamosse_progress.MODE_NORMAL:
      if not self._is_determinate():
        self.stop()
        self._setvar(0)
    elif value == yamosse_progress.MODE_LOADING:
      if self._is_determinate():
        self._setvar(0)
        self.start()
    
    self._mode_state_taskbar()
  
  @property
  def variable(self):
    return self._variable
  
  @property.setter
  def variable(self, value):
    cbname = self._cbname
    
    if cbname:
      super().trace_remove('write', cbname)
    
    self._variable = value if value else tk.IntVar()
    self._cbname = super().trace_add('write', self._show)
    
    self._show()
  
  def _getvar(self):
    return super().tk.getvar(str(self._variable))
  
  def _setvar(self, value):
    return super().tk.setvar(str(self._variable), value)
  
  def _is_determinate(self):
    return str(self['mode']) == 'determinate'
  
  def _command_taskbar(self, command):
    taskbar = self.taskbar
    
    if not taskbar:
      return None
    
    type_ = yamosse_progress.types[command]
    
    if type_ is None:
      return None
    
    return getattr(taskbar, type_)()
  
  def _mode_state_taskbar(self):
    taskbar = self.taskbar
    
    if not taskbar:
      return None
    
    type_ = yamosse_progress.types[self['mode']]
    
    if type_ is None:
      type_ = self._state_type
    
    return taskbar.set_progress_type(type_)
  
  def _show(self, *args, **kwargs):
    # only update the percent label in determinate mode
    if self._is_determinate(progressbar):
      value = int(self._getvar())
      
      if taskbar:
        taskbar.set_progress(value, int(progressbar['maximum']))
      
      self._value = value
    
    self.percent['text'] = '%d%%' % self._value