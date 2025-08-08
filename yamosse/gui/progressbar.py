import tkinter as tk
from tkinter import ttk

import yamosse.progress as yamosse_progress

from .. import gui


def _is_determinate_progressbar(progressbar):
  return str(progressbar['mode']) == 'determinate'


def configure_progressbar(widgets, variable, type_):
  progressbar, taskbar = widgets
  variable_set = False
  
  if type_ not in yamosse_progress.types:
    variable.set(int(type_))
    return True
  
  if type_ == yamosse_progress.LOADING:
    if _is_determinate_progressbar(progressbar):
      progressbar['mode'] = 'indeterminate'
      variable.set(0) # must be done after setting mode to take effect
      variable_set = True
      progressbar.start() # as the last step, start the animation
  else:
    if not _is_determinate_progressbar(progressbar):
      progressbar.stop() # as the first step, stop the animation
      progressbar['mode'] = 'determinate'
      variable.set(0) # must be done after setting mode to take effect
      variable_set = True
    
    if type_ == yamosse_progress.DONE:
      variable.set(int(progressbar['maximum']))
      
      if taskbar: taskbar.flash_done()
      return True
    
    if type_ == yamosse_progress.RESET:
      variable.set(0)
      
      if taskbar: taskbar.reset()
      return True
  
  if taskbar: taskbar.set_progress_type(yamosse_progress.types[type_])
  return variable_set


def make_progressbar(frame, name='', variable=None,
  type_=yamosse_progress.NORMAL, parent=None, task=False, **kwargs):
  if not variable: variable = tk.IntVar()
  
  frame.rowconfigure(0, weight=1) # make progressbar vertically centered
  frame.columnconfigure(1, weight=1) # make progressbar horizontally resizable
  
  percent_label = gui.make_percent(frame)
  
  progressbar = ttk.Progressbar(frame, variable=variable,
    mode='determinate', orient=tk.HORIZONTAL, **kwargs)
  
  progressbar.grid(row=0, column=1, sticky=tk.EW)
  
  taskbar = None
  
  if task and yamosse_progress.PyTaskbar:
    if not parent: parent = frame.winfo_toplevel()
    taskbar = yamosse_progress.PyTaskbar.Progress(hwnd=yamosse_progress.hwnd(parent))
  
  value = 0
  
  def show(*args, **kwargs):
    nonlocal value
    
    # only update the percent label in determinate mode
    if _is_determinate_progressbar(progressbar):
      value = variable.get()
      
      if taskbar:
        taskbar.set_progress(value, int(progressbar['maximum']))
    
    text = '%d%%' % value
    percent_label['text'] = text
  
  variable.trace('w', show)
  
  widgets = (progressbar, taskbar)
  if not configure_progressbar(widgets, variable, type_): show()
  return gui.make_name(frame, name), widgets, percent_label