from abc import ABC, abstractmethod
from threading import Thread, Event

import yamosse.utils as yamosse_utils

try: from . import gui
except ImportError: gui = None

class SubsystemExit(Exception): pass
class SubsystemError(Exception): pass


def subsystem(window, title, variables):
  class Subsystem(ABC):
    @staticmethod
    @abstractmethod
    def start(target, *args, **kwargs):
      pass
    
    @abstractmethod
    def show(self, values=None):
      pass
    
    def error(self, message, *args, **kwargs):
      raise SubsystemError(message)
    
    @abstractmethod
    def confirm(self, message, *args, **kwargs):
      pass
    
    def variables_from_attrs(self, object_):
      pass
    
    def attrs_to_variables(self, object_):
      pass
    
    def get_variable_or_attr(self, object_, key):
      return getattr(object_, key)
    
    def set_variable_and_attr(self, object_, key, value):
      setattr(object_, key, value)
    
    def quit(self):
      pass
  
  class WindowSubsystem(Subsystem):
    def __init__(self, window, title, variables):
      assert gui, 'gui module must be loaded'
      
      self.window = window
      self.title = title
      self.variables = variables
      
      self.show_callback = None
      self.widgets = None
    
    @staticmethod
    def start(target, *args, daemon=False, **kwargs):
      gui.threaded()
      
      # start a thread so the GUI isn't blocked
      Thread(target=target, args=args, daemon=daemon, kwargs=kwargs).start()
    
    def show(self, values=None):
      if not self.show_callback(self.widgets, values=values): raise SubsystemExit
    
    def error(self, message, *args, parent=None, **kwargs):
      gui.messagebox.showwarning(
        parent=parent if parent else self.window,
        title=title,
        message=message
      )
    
    def confirm(self, message, *args, default=None, parent=None, **kwargs):
      if default is not None:
        default = gui.messagebox.YES if default else gui.messagebox.NO
      
      return gui.messagebox.askyesno(
        parent=parent if parent else self.window,
        title=title,
        message=message,
        default=default
      )
    
    def variables_from_attrs(self, object_):
      self.variables = gui.get_variables_from_attrs(object_)
    
    def attrs_to_variables(self, object_):
      gui.set_attrs_to_variables(self.variables, object_)
    
    def get_variable_or_attr(self, object_, key):
      # it is expected this function will not be called from the GUI thread
      # (because otherwise, you'd just get the variable directly)
      # so here we automate getting the variable on the other thread n' waiting...
      value = super().get_variable_or_attr(object_, key)
      event = Event()
      
      def callback():
        nonlocal value
        
        value = self.variables[key].get()
        event.set()
      
      if gui.after_idle_window(self.window, callback):
        event.wait()
      
      return value
    
    def set_variable_and_attr(self, object_, key, value):
      super().set_variable_and_attr(object_, key, value)
      event = Event()
      
      def callback():
        self.variables[key].set(value)
        event.set()
      
      if gui.after_idle_window(self.window, callback):
        event.wait()
    
    def quit(self):
      self.window.quit()
  
  class ConsoleSubsystem(Subsystem):
    @staticmethod
    def start(target, *args, daemon=False, **kwargs):
      target(*args, **kwargs)
    
    def show(self, values=None):
      if values and 'log' in values:
        print(yamosse_utils.ascii_backslashreplace(values['log']))
    
    def confirm(self, message, *args, default=None, **kwargs):
      YES = 'y'
      NO = 'n'
      
      yes = YES
      no = NO
      
      default_has_value = default is not None
      
      if default_has_value:
        if default: yes = yes.upper()
        else: no = no.upper()
      
      result = ''
      
      while not result:
        prompt = ''
        
        if message:
          prompt = '%s [%c/%c]\n' % (message, yes, no)
          message = ''
        else:
          prompt = 'Please enter %c or %c.\n' % (yes, no)
        
        result = input(prompt).strip()
        
        if result:
          result = result[0].casefold()
          
          if result not in (YES, NO):
            result = ''
        elif default_has_value: return default
      
      return result == YES
  
  if window:
    return WindowSubsystem(window, title, variables)
  
  return ConsoleSubsystem()