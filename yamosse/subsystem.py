from abc import ABC, abstractmethod
from threading import Thread

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
    
    @abstractmethod
    def streaming(self, callback):
      pass
    
    def variables_from_object(self, object_):
      return None
    
    def variables_to_object(self, object_):
      pass
    
    def set_variable_after_idle(self, key, value):
      pass
    
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
      self.stop_event = None
    
    @staticmethod
    def start(target, *args, **kwargs):
      gui.threaded()
      
      # start a thread so the GUI isn't blocked
      Thread(target=target, args=args, kwargs=kwargs).start()
    
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
    
    def streaming(self, callback):
      callback()
      
      stop_event = self.stop_event
      
      if stop_event.is_set():
        stop_event.clear()
        return False
      
      return True
    
    def variables_from_object(self, object_):
      self.variables = gui.get_variables_from_object(object_)
    
    def variables_to_object(self, object_):
      gui.set_variables_to_object(self.variables, object_)
    
    def set_variable_after_idle(self, key, value):
      def callback():
        self.variables[key].set(value)
      
      if not gui.after_idle_window(self.window, callback): raise SubsystemExit
    
    def quit(self):
      self.window.quit()
  
  class ConsoleSubsystem(Subsystem):
    @staticmethod
    def start(target, *args, **kwargs):
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
    
    def streaming(self, callback):
      try:
        callback()
        return True
      except KeyboardInterrupt:
        pass
      
      return False
  
  if window:
    return WindowSubsystem(window, title, variables)
  
  return ConsoleSubsystem()