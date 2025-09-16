from abc import ABC, abstractmethod
from threading import Thread

import yamosse.utils as yamosse_utils

try:
  from . import gui
except ImportError:
  gui = None

class SubsystemExit(Exception): pass
class SubsystemError(Exception): pass


class _Subsystem(ABC):
  def __enter__(self):
    return self
  
  def __exit__(self, exc, val, tb):
    self.close()
  
  def close(self):
    pass
  
  @abstractmethod
  def start(self, target, args=None, kwargs=None):
    pass
  
  @abstractmethod
  def show(self, exit_, values=None):
    if exit_.is_set():
      raise SubsystemExit
  
  def error(self, message, *args, **kwargs):
    raise SubsystemError(message)
  
  @abstractmethod
  def confirm(self, message, *args, **kwargs):
    pass
  
  def variables_from_attrs(self, attrs):
    pass
  
  def attrs_to_variables(self, attrs):
    pass
  
  def get_variable_or_attr(self, attrs, key):
    return getattr(attrs, key)
  
  def set_variable_and_attr(self, attrs, key, value):
    setattr(attrs, key, value)
  
  def quit(self):
    pass


class _WindowSubsystem(_Subsystem):
  def __init__(self, window, title, variables):
    assert gui, 'gui module must be loaded'
    
    self._window = window
    self._title = title
    self._variables = variables
    
    self._threads = []
    
    self.show_callback = None
    self.widgets = None
  
  def close(self):
    # if we are just quitting don't do anything
    if self._window.children: return
    
    # ensure we are the last thread to be alive
    for thread in self._threads:
      thread.join()
  
  def start(self, target, args=None, kwargs=None):
    gui.threaded()
    
    # filter out dead threads
    self._threads = threads = list(filter(
      lambda thread: thread.is_alive(),
      self._threads
    ))
    
    # start a thread so the GUI isn't blocked
    thread = Thread(target=target, args=args or (), kwargs=kwargs or {})
    thread.start()
    
    # after starting the thread so it is alive, append it to the threads list
    threads.append(thread)
  
  def show(self, exit_, values=None):
    super().show(exit_, values=values)
    
    if not self.show_callback(self.widgets, values=values):
      raise SubsystemExit
  
  def error(self, message, *args, parent=None, **kwargs):
    gui.messagebox.showwarning(
      parent=parent or self._window,
      title=self._title,
      message=message
    )
  
  def confirm(self, message, *args, default=None, parent=None, **kwargs):
    if default is not None:
      default = gui.messagebox.YES if default else gui.messagebox.NO
    
    return gui.messagebox.askyesno(
      parent=parent or self._window,
      title=self._title,
      message=message,
      default=default
    )
  
  def variables_from_attrs(self, attrs):
    self._variables = gui.get_variables_from_attrs(attrs)
  
  def attrs_to_variables(self, attrs):
    # we don't expose copy_attrs_to_variables which should only be used by the GUI
    # because it does not handle for the scenario where
    # attrs has a different variable type than the existing variable
    gui.set_attrs_to_variables(self._variables, attrs)
  
  def get_variable_or_attr(self, attrs, key):
    # it is expected this function will not be called from the GUI thread
    # (because otherwise, you'd just get the variable directly)
    # so here we automate getting the variable on the other thread n' waiting...
    value = super().get_variable_or_attr(attrs, key)
    
    def callback():
      nonlocal value
      
      value = self._variables[key].get()
    
    gui.after_wait_window(self._window, callback)
    return value
  
  def set_variable_and_attr(self, attrs, key, value):
    super().set_variable_and_attr(attrs, key, value)
    
    gui.after_wait_window(
      self._window,
      lambda: self._variables[key].set(value)
    )
  
  def quit(self):
    self._window.quit()


class _ConsoleSubsystem(_Subsystem):
  def start(self, target, args=None, kwargs=None):
    target(*(args or ()), **(kwargs or {}))
  
  def show(self, exit_, values=None):
    super().show(exit_, values=values)
    
    if values and 'log' in values:
      print(yamosse_utils.ascii_backslashreplace(values['log']))
  
  def confirm(self, message, *args, default=None, **kwargs):
    YES = 'y'
    NO = 'n'
    RESULTS = (YES, NO)
    
    yes, no = RESULTS
    
    default_has_value = default is not None
    
    if default_has_value:
      if default:
        yes = yes.upper()
      else:
        no = no.upper()
    
    result = ''
    
    while not result:
      prompt = ''
      
      if message:
        prompt = '%s [%c/%c]\n' % (message, yes, no)
        message = ''
      else:
        prompt = 'Please enter %c or %c.\n' % (yes, no)
      
      result = input(prompt).lstrip()
      
      if result:
        result = result[0].casefold()
        
        if result not in RESULTS:
          result = ''
      elif default_has_value:
        return default
    
    return result == YES


def subsystem(window, title, variables):
  if window:
    return _WindowSubsystem(window, title, variables)
  
  return _ConsoleSubsystem()