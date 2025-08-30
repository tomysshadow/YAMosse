from tempfile import NamedTemporaryFile
import os
import platform
import subprocess
import weakref


class _HiddenFileWrapper:
  def __init__(self, *args, prefix='', **kwargs):
    HIDDEN = '~'
    
    self._system = platform.system()
    
    self._args = args
    self._prefix = prefix
    self._kwargs = kwargs
    
    tmp = NamedTemporaryFile(
      *args,
      delete=False,
      prefix='%c%s' % (HIDDEN, prefix),
      **kwargs
    )
    
    self.tmp = tmp
    self.save = False
    self._hide(True)
    
    self.name = None
  
  def close(self, *args, **kwargs):
    tmp = self.tmp
    
    self._hide(False)
    tmp.close(*args, **kwargs)
    save = self.save
    
    if save:
      if not isinstance(save, str):
        with NamedTemporaryFile(
          *self._args,
          delete=False,
          prefix=self._prefix,
          **self._kwargs
        ) as visible:
          save = visible.name
      
      os.replace(tmp.name, save)
      self.name = save
    else:
      os.unlink(tmp.name)
  
  def _hide(self, hidden):
    if self._system == 'Windows':
      subprocess.run(
        ('attrib', '+h' if hidden else '-h', self.tmp.name),
        check=True
      )


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
  
  def close(self, *args, **kwargs):
    self.__closer(*args, **kwargs)
  
  @property
  def name(self):
    name = self.__wrapper.name
    
    if name:
      return name
    
    return self.__wrapper.tmp.name
  
  @property
  def save(self):
    return self.__wrapper.save
  
  @save.setter
  def save(self, value):
    self.__wrapper.save = value