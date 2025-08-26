import tkinter as tk
from tkinter import ttk

import yamosse.progress as yamosse_progress
import yamosse.utils as yamosse_utils

from .. import gui

COMMAND_RESET_STATES = ['!%s' % s for s in yamosse_progress.STATES if s]


class Progressbar(ttk.Progressbar):
  def __init__(self, frame, name='', variable=None,
  mode=yamosse_progress.MODE_DETERMINATE,
  parent=None, task=False, percent=True, **kwargs):
    frame.rowconfigure(0, weight=1) # make progressbar vertically centered
    frame.columnconfigure(1, weight=1) # make progressbar horizontally resizable
    
    self.name_frame = gui.make_name(frame, name)
    
    progressbar = super()
    progressbar.__init__(frame, **kwargs)
    progressbar.grid(row=0, column=1, sticky=tk.EW)
    
    taskbar = None
    
    if task and yamosse_progress.PyTaskbar:
      if not parent:
        parent = frame.winfo_toplevel()
      
      taskbar = yamosse_progress.PyTaskbar.Progress(
        hwnd=yamosse_progress.hwnd(parent)
      )
    
    self._taskbar = taskbar
    
    percent_label = None
    
    if percent:
      percent_label = gui.make_percent(frame)
    
    self._percent_label = percent_label
    
    self._state_type = yamosse_progress.types[yamosse_progress.STATE_NORMAL]
    self._variable = None
    self._trace_cbname = self.register(self._trace)
    self._value = 0
    
    self.variable = variable
    self.mode = mode
    
    # show or hide taskbar progress with the widget
    self.bind('<Map>', self._open_task)
    
    for name in ('<Unmap>', '<Destroy>'):
      self.bind(name, self._close_task)
  
  def configure(self, cnf={}, **kw):
    kw = cnf | kw
    kw_len = len(kw)
    
    if kw_len == 0: # return all options
      return super().configure()
    
    if kw_len == 1 and next(iter(kw.values())) is None: # return argument values
      return super().configure(**kw)
    
    try:
      self.variable = kw.pop('variable')
    except KeyError:
      pass
    
    try:
      self.mode = kw.pop('mode')
    except KeyError:
      pass
    
    return super().configure(**kw)
  
  def set(self, value):
    if value in yamosse_progress.COMMANDS:
      self.command(value)
    elif value in yamosse_progress.MODES:
      self.mode = value
    elif yamosse_progress.is_state(value):
      self.state(value)
    else:
      self._setvar(value)
  
  def command(self, command):
    if command not in yamosse_progress.COMMANDS:
      raise ValueError('command must be in %r' % (yamosse_progress.COMMANDS,))
    
    # the taskbar should only flash in the normal state
    # because it also resets the progress type
    # so it would become out of sync with the progress bar otherwise
    if command == yamosse_progress.COMMAND_DONE:
      self.mode = yamosse_progress.MODE_DETERMINATE
      self._setvar(int(self['maximum']))
      if self.state(): return
    elif command == yamosse_progress.COMMAND_RESET:
      self.state(COMMAND_RESET_STATES)
      self.mode = yamosse_progress.MODE_DETERMINATE
      self._setvar(0)
    
    # in future there might be taskbar only commands
    # so this is outside of the main if...elif block
    self._command_task(command)
  
  def state(self, statespec=None):
    # we intentionally don't check that the states are in STATES
    # because other Tkinter states are still allowed here
    result = super().state(statespec=statespec)
    
    # we only need to do stuff when setting the state
    # so if we're only getting the state, just return here
    if statespec is None:
      return result
    
    # get the highest priority state
    # so the taskbar knows what type to use
    for state in yamosse_progress.STATES:
      if not self.instate((state,)):
        continue
      
      state_type = yamosse_progress.types[state]
      
      if state_type is not None:
        self._state_type = state_type
        break
    
    self._mode_state_task()
    return result
  
  @property
  def mode(self):
    return str(self['mode'])
  
  @mode.setter
  def mode(self, value):
    DETERMINATE = yamosse_progress.MODE_DETERMINATE
    
    mode = self.mode
    
    if value == DETERMINATE and mode != DETERMINATE:
      # exit determinate mode
      self.stop() # as the first step, stop the animation
      super().configure(mode=value)
      self._setvar(0) # must be done after setting mode to take effect
    elif value != DETERMINATE and mode == DETERMINATE:
      # enter determinate mode
      super().configure(mode=value)
      self._setvar(0) # must be done after setting mode to take effect
      self.start() # as the last step, start the animation
    else:
      super().configure(mode=value)
    
    self._mode_state_task()
  
  @property
  def variable(self):
    return self._variable
  
  @variable.setter
  def variable(self, value):
    # we manually call trace add/remove here
    # juuust in case configure gets called with a string variable name
    variable = self._variable
    trace_cbname = self._trace_cbname
    
    if variable is not None:
      self.tk.call('trace', 'remove', 'variable',
        variable, 'write', trace_cbname)
    
    variable = value if value else tk.IntVar()
    
    self.tk.call('trace', 'add', 'variable',
      variable, 'write', trace_cbname)
    
    super().configure(variable=variable)
    self._variable = variable
    
    self._show()
  
  @property
  def taskbar(self):
    if not self.winfo_ismapped():
      return None
    
    return self._taskbar
  
  @taskbar.setter
  def taskbar(self, value):
    self._close_task()
    self._taskbar = value
    self._open_task()
  
  @property
  def percent_label(self):
    return self._percent_label
  
  @percent_label.setter
  def percent_label(self, value):
    self._percent_label = value
    self._show(task=False)
  
  def _getvar(self):
    return self.getvar(str(self._variable))
  
  def _setvar(self, value):
    self.setvar(str(self._variable), value)
  
  def _trace(self, *args, **kwargs):
    self._show()
  
  def _show(self, percent=True, task=True):
    # only update the percent label in determinate mode
    if self.mode == yamosse_progress.MODE_DETERMINATE:
      value = int(self._getvar())
      
      if task:
        taskbar = self.taskbar
        
        if taskbar:
          taskbar.set_progress(value, int(self['maximum']))
      
      self._value = value
    
    if percent:
      percent_label = self._percent_label
      
      if percent_label:
        percent_label['text'] = '%d%%' % self._value
  
  def _command_task(self, command):
    taskbar = self.taskbar
    
    if not taskbar:
      return
    
    type_ = yamosse_progress.types[command]
    
    if type_ is None:
      return
    
    getattr(taskbar, type_)()
  
  def _mode_state_task(self):
    taskbar = self.taskbar
    
    if not taskbar:
      return
    
    type_ = yamosse_progress.types[self.mode]
    
    if type_ is None:
      type_ = self._state_type
    
    taskbar.set_progress_type(type_)
  
  def _open_task(self, e):
    self._mode_state_task()
    self._show(percent=False)
  
  def _close_task(self, e):
    self._command_task(yamosse_progress.COMMAND_RESET)