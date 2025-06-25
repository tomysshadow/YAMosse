from abc import ABC, abstractmethod

from .gui import gui

def subsystem(window, title):
  class Subsystem(ABC):
    @abstractmethod
    def ask_yes_no(self, message, default, parent=None):
      pass
    
    @abstractmethod
    def show_warning(self, message, parent=None):
      pass
    
    @abstractmethod
    def quit(self):
      pass
  
  class ConsoleSubsystem(Subsystem):
    def ask_yes_no(self, message, default, parent=None):
      return True
    
    def show_warning(self, message, parent=None):
      print(message)
    
    def quit(self):
      pass
  
  class WindowSubsystem(Subsystem):
    def __init__(self, window, title):
      self.window = window
      self.title = title
    
    def ask_yes_no(self, message, default, parent=None):
      return gui.messagebox.askyesno(parent=parent if parent else self.window, title=title, message=message, default=default)
      
      return True
    
    def show_warning(self, message, parent=None):
      gui.messagebox.showwarning(parent=parent if parent else self.window, title=title, message=message)
      return
      
      print(message)
    
    def quit(self):
      self.window.quit()
  
  if window:
    return WindowSubsystem(window, title)
  
  return ConsoleSubsystem()