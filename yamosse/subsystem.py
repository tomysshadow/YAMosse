from abc import ABC, abstractmethod
from threading import Thread

from .gui import gui

class SubsystemExit(Exception): pass


def ascii_replace(value):
  return str(value).encode('ascii', 'replace').decode()


def latin1_unescape(value):
  return str(value).encode('latin1').decode('unicode_escape')


def subsystem(window, title):
  class Subsystem(ABC):
    @abstractmethod
    def start(self, target, *args, **kwargs):
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
    
    def get_variables_from_object(self, object_):
      return None
    
    def set_variables_to_object(self, variables, object_):
      pass
    
    def quit(self):
      pass
  
  class WindowSubsystem(Subsystem):
    def __init__(self, window, title):
      self.window = window
      self.title = title
    
    def start(self, target, *args, **kwargs):
      gui.threaded()
      
      # start a thread so the GUI isn't blocked
      Thread(target=target, args=args, kwargs=kwargs).start()
    
    def show(self, values=None):
      if not self.show_values_callback(self.widgets, values=values):
        raise SubsystemExit
    
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
    
    def get_variables_from_object(self, object_):
      return gui.get_variables_from_object(object_)
    
    def set_variables_to_object(self, variables, object_):
      gui.set_variables_to_object(variables, object_)
    
    def quit(self):
      self.window.quit()
  
  class ConsoleSubsystem(Subsystem):
    def start(self, target, *args, **kwargs):
      target(*args, **kwargs)
    
    def show(self, values=None):
      if values and 'log' in values:
        print(ascii_replace(values['log']))
    
    def show_warning(self, message, parent=None):
      print(message)
    
    def ask_yes_no(self, message, default=None, parent=None):
      YES = 'Y'
      NO = 'N'
      
      yes = 'y'
      no = 'n'
      
      default_has_value = not default is None
      
      if default_has_value:
        if default:
          yes = YES
        else:
          no = NO
      
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
        elif default_has_value:
          return YES if default else NO
      
      return result == YES
  
  if window:
    return WindowSubsystem(window, title)
  
  return ConsoleSubsystem()