from abc import ABC, abstractmethod

from .gui import gui

def subsystem(window, title):
  class Subsystem(ABC):
    @abstractmethod
    def ask_yes_no(self, message, default=None, parent=None):
      pass
    
    @abstractmethod
    def show_warning(self, message, parent=None):
      pass
    
    @abstractmethod
    def get_variables_from_object(self, object_):
      return None
    
    @abstractmethod
    def set_variables_to_object(self, variables, object_):
      pass
    
    @abstractmethod
    def threaded(self):
      pass
    
    @abstractmethod
    def quit(self):
      pass
  
  class WindowSubsystem(Subsystem):
    def __init__(self, window, title):
      self.window = window
      self.title = title
    
    def ask_yes_no(self, message, default=None, parent=None):
      if not default is None:
        default = gui.messagebox.YES if default else gui.messagebox.NO
      
      return gui.messagebox.askyesno(
        parent=parent if parent else self.window,
        title=title,
        message=message,
        default=default
      )
    
    def show_warning(self, message, parent=None):
      gui.messagebox.showwarning(
        parent=parent if parent else self.window,
        title=title,
        message=message
      )
      return
    
    def get_variables_from_object(self, object_):
      return gui.get_variables_from_object(object_)
    
    def set_variables_to_object(self, variables, object_):
      gui.set_variables_to_object(variables, object_)
    
    def threaded(self):
      gui.threaded()
    
    def quit(self):
      self.window.quit()
  
  class ConsoleSubsystem(Subsystem):
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
    
    def show_warning(self, message, parent=None):
      print(message)
  
  if window:
    return WindowSubsystem(window, title)
  
  return ConsoleSubsystem()