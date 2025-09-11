import tkinter as tk
from tkinter import ttk
from contextlib import suppress
from weakref import WeakValueDictionary

import yamosse.progress as yamosse_progress
import yamosse.utils as yamosse_utils

from .. import gui
from . import trace as gui_trace

STATES_OFF = [s.off() for s in yamosse_progress.State]


class Progressbar(ttk.Progressbar):
  _hwnds = WeakValueDictionary()
  
  def __init__(self, frame, name='', variable=None,
  mode=yamosse_progress.Mode.DETERMINATE,
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
      
      hwnd = yamosse_progress.hwnd(parent)
      hwnds = self._hwnds
      
      if hwnds.setdefault(hwnd, self) is not self:
        raise RuntimeError('hwnd must not have multiple Progressbar tasks')
      
      self.bind('<Destroy>', lambda e: hwnds.pop(hwnd, None), add=True)
      
      taskbar = yamosse_progress.PyTaskbar.Progress(hwnd=hwnd)
    
    self._taskbar = taskbar
    
    percent_label = None
    
    if percent:
      percent_label = gui.make_percent(frame)
    
    self._percent_label = percent_label
    
    self._trace = None
    self._variable = None
    self._state_type = yamosse_progress.types[yamosse_progress.State.NORMAL]
    self._value = 0
    
    self.variable = variable
    self.mode = mode
    
    # show or hide taskbar progress with the widget
    self.bind('<Map>', lambda e: self._open_task(), add=True)
    
    for sequence in ('<Unmap>', '<Destroy>'):
      self.bind(sequence, lambda e: self._close_task(), add=True)
  
  def __getattr__(self, name):
    try:
      function = yamosse_progress.Function(name)
    except ValueError as exc:
      raise AttributeError from exc
    
    # variadics are supported in case there is ever a function that uses them
    # (but currently there aren't any)
    return lambda *args, **kwargs: self.function(
      function, args=args, kwargs=kwargs)
  
  def configure(self, cnf={}, **kw):
    kw = cnf | kw
    kw_len = len(kw)
    
    if kw_len == 0: # return all options
      return super().configure()
    
    if kw_len == 1 and next(iter(kw.values())) is None: # return argument values
      return super().configure(**kw)
    
    with suppress(KeyError):
      self.variable = kw.pop('variable')
    
    with suppress(KeyError):
      self.mode = yamosse_progress.Mode(str(kw.pop('mode')))
    
    return super().configure(**kw)
  
  def get(self):
    return int(float(self.getvar(str(self.variable))))
  
  def set(self, value):
    self.setvar(str(self.variable), int(float(value)))
  
  def function(self, function, args=None, kwargs=None):
    # these functions return True if the associated taskbar
    # function should run, False otherwise
    # the taskbar should only flash in the normal state
    # because it also resets the progress type
    # so it would become out of sync with the progress bar otherwise
    def done():
      self.mode = yamosse_progress.Mode.DETERMINATE
      self.set(self['maximum'])
      return not self.state()
    
    def reset():
      self.state(STATES_OFF)
      self.mode = yamosse_progress.Mode.DETERMINATE
      self.set(0)
      return True
    
    if ({
      yamosse_progress.Function.DONE: done,
      yamosse_progress.Function.RESET: reset,
    })[function]():
      self._function_task(function)
  
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
    # (the State enum is lowest to highest priority, so must be reversed)
    for state in reversed(yamosse_progress.State):
      if not self.instate((state.on(),)):
        continue
      
      state_type = yamosse_progress.types[state]
      
      if state_type is not None:
        self._state_type = state_type
        break
    
    self._state_mode_task()
    return result
  
  @property
  def mode(self):
    return yamosse_progress.Mode(str(self['mode']))
  
  @mode.setter
  def mode(self, value):
    DETERMINATE = yamosse_progress.Mode.DETERMINATE
    
    mode = self.mode
    
    if value == DETERMINATE and mode != DETERMINATE:
      # exit determinate mode
      self.stop() # as the first step, stop the animation
      super().configure(mode=value.value)
      self.set(0) # must be done after setting mode to take effect
    elif value != DETERMINATE and mode == DETERMINATE:
      # enter determinate mode
      super().configure(mode=value.value)
      self.set(0) # must be done after setting mode to take effect
      self.start() # as the last step, start the animation
    else:
      super().configure(mode=value.value)
    
    self._state_mode_task()
  
  @property
  def variable(self):
    return self._variable
  
  @variable.setter
  def variable(self, value):
    if not value:
      value = tk.IntVar()
    
    super().configure(variable=value)
    
    self._trace = gui_trace.Trace(
      self,
      'write',
      lambda name1, name2, op: self._show()
    )
    
    # even though we can get the variable from the trace
    # doing it this way ensures that the variable stays alive with the widget
    self._variable = value
    self._show()
  
  @property
  def taskbar(self):
    if not self.winfo_viewable():
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
  
  def _show(self, percent=True, task=True):
    # only update the value in determinate mode
    if self.mode == yamosse_progress.Mode.DETERMINATE:
      value = self.get()
      
      if task:
        taskbar = self.taskbar
        
        if taskbar:
          taskbar.set_progress(value, int(self['maximum']))
      
      self._value = value
    
    if percent:
      percent_label = self._percent_label
      
      if percent_label:
        percent_label['text'] = '%d%%' % self._value
  
  def _function_task(self, function, args=None, kwargs=None):
    taskbar = self.taskbar
    
    if not taskbar:
      return
    
    type_ = yamosse_progress.types[function]
    
    if type_ is None:
      return
    
    getattr(taskbar, type_)(*(args or ()), **(kwargs or {}))
  
  def _state_mode_task(self):
    taskbar = self.taskbar
    
    if not taskbar:
      return
    
    type_ = yamosse_progress.types[self.mode]
    
    if type_ is None:
      type_ = self._state_type
    
    taskbar.set_progress_type(type_)
  
  def _open_task(self):
    self._state_mode_task()
    self._show(percent=False)
  
  def _close_task(self):
    self._function_task(yamosse_progress.Function.RESET)