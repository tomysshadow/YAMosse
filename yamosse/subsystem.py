from abc import ABC, abstractmethod
from threading import Thread

import yamosse.encoding as yamosse_encoding

try: from .gui import gui
except ImportError: gui = None

class SubsystemExit(Exception): pass


def subsystem(window, title, variables):
  class Subsystem(ABC):
    @staticmethod
    @abstractmethod
    def start(target, *args, **kwargs):
      pass
    
    @abstractmethod
    def show(self, values=None):
      pass
    
    @abstractmethod
    def show_warning(self, message, parent=None):
      pass
    
    @abstractmethod
    def ask_yes_no(self, message, default=None, parent=None):
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
    
    @staticmethod
    def start(target, *args, **kwargs):
      gui.threaded()
      
      # start a thread so the GUI isn't blocked
      Thread(target=target, args=args, kwargs=kwargs).start()
    
    def show(self, values=None):
      if not self.show_callback(self.widgets, values=values): raise SubsystemExit
    
    def show_warning(self, message, parent=None):
      gui.messagebox.showwarning(
        parent=parent if parent else self.window,
        title=title,
        message=message
      )
      return
    
    def ask_yes_no(self, message, default=None, parent=None):
      if not default is None:
        default = gui.messagebox.YES if default else gui.messagebox.NO
      
      return gui.messagebox.askyesno(
        parent=parent if parent else self.window,
        title=title,
        message=message,
        default=default
      )
    
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
    
    @staticmethod
    def show(values=None):
      if values and 'log' in values:
        print(yamosse_encoding.ascii_backslashreplace(values['log']))
    
    @staticmethod
    def show_warning(message, parent=None):
      print(message)
    
    @staticmethod
    def ask_yes_no(message, default=None, parent=None):
      YES = 'Y'
      NO = 'N'
      
      yes = 'y'
      no = 'n'
      
      default_has_value = not default is None
      
      if default_has_value:
        if default: yes = YES
        else: no = NO
      
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
          result = result[0].upper()
          
          if result != YES and result != NO:
            result = ''
        elif default_has_value: return default
      
      return result == YES
  
  if window: return WindowSubsystem(window, title, variables)
  return ConsoleSubsystem()