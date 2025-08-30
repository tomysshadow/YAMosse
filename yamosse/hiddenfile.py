from tempfile import NamedTemporaryFile
import os
import platform
import subprocess

HIDDEN = '~'


class HiddenFile:
  def __init__(self, *args, prefix='', **kwargs):
    self.__system = platform.system()
    
    self.__tmp = NamedTemporaryFile(
      *args,
      delete=False,
      prefix='%c%s' % (HIDDEN, prefix),
      **kwargs
    )
    
    self.save_name = None
    self.__hide(True)
  
  def __getattr__(self, name):
    return getattr(self.__tmp, name)
  
  def __enter__(self):
    return self
  
  def __exit__(self, *args, **kwargs):
    self.close()
  
  def close(self, *args, **kwargs):
    self.__hide(False)
    self.__tmp.close(*args, **kwargs)
    save_name = self.save_name
    
    if save_name:
      os.replace(self.name, save_name)
      self.name = save_name
    else:
      os.unlink(self.name)
  
  def __hide(self, hidden):
    if self.__system == 'Windows':
      subprocess.run(('attrib', '+h' if hidden else '-h', self.name), check=True)
  
  @property
  def visible_name(self):
    head, tail = os.path.split(self.name)
    return os.path.join(head, tail.removeprefix(HIDDEN))