from tempfile import NamedTemporaryFile
import os
import platform
import subprocess
import weakref


class _HiddenFileWrapper:
  def __init__(self, *args, prefix='', **kwargs):
    HIDDEN = '~'
    
    self._system = platform.system()
    
    tmp = NamedTemporaryFile(
      *args,
      delete=False,
      prefix='%c%s' % (HIDDEN, prefix),
      **kwargs
    )
    
    self.tmp = tmp
    self.save_name = None
    self._hide(True)
    
    self.name = None
    
    head, tail = os.path.split(tmp.name)
    self.visible_name = os.path.join(head, tail.removeprefix(HIDDEN))
  
  def close(self, *args, **kwargs):
    self._hide(False)
    self.tmp.close(*args, **kwargs)
    save_name = self.save_name
    
    if save_name:
      os.replace(self.tmp.name, save_name)
      self.name = save_name
    else:
      os.unlink(self.tmp.name)
  
  def _hide(self, hidden):
    if self._system == 'Windows':
      subprocess.run(('attrib', '+h' if hidden else '-h', self.tmp.name), check=True)


class HiddenFile:
  def __init__(self, *args, **kwargs):
    wrapper = _HiddenFileWrapper(*args, **kwargs)
    
    self.__wrapper = wrapper
    self.__closer = weakref.finalize(self, wrapper.close)
  
  def __getattr__(self, name):
    return getattr(self.__wrapper.tmp, name)
  
  def __enter__(self):
    return self
  
  def __exit__(self, *args, **kwargs):
    self.__closer()
  
  @property
  def name(self):
    name = self.__wrapper.name
    
    if name:
      return name
    
    return self.__wrapper.tmp.name
  
  @property
  def save_name(self):
    return self.__wrapper.save_name
  
  @save_name.setter
  def save_name(self, value):
    self.__wrapper.save_name = value
  
  @property
  def visible_name(self):
    return self.__wrapper.visible_name