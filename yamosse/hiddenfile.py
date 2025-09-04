from tempfile import NamedTemporaryFile
import os
import platform
import subprocess
import weakref

import yamosse.utils as yamosse_utils

HIDDEN = '~'


class _HiddenFileWrapper:
  def __init__(self, *args, prefix='', **kwargs):
    self._system = platform.system()
    
    self._args = args
    self._prefix = prefix
    self._kwargs = kwargs
    
    self.save = False
    
    self.tmp = NamedTemporaryFile(
      *args,
      delete=False,
      prefix=yamosse_utils.str_ensureprefix(prefix, HIDDEN),
      **kwargs
    )
    
    self._hide(True)
  
  def close(self):
    tmp = self.tmp
    
    self._hide(False)
    tmp.close()
    save = self.save
    
    if not save:
      os.unlink(tmp.name)
      self.name = None
      return
    
    # generate a new visible name to use
    # we can't just strip the tilde (~) off the current name
    # because then it wouldn't be guaranteed unique anymore
    with NamedTemporaryFile(
      *self._args,
      delete=False,
      prefix=self._prefix,
      **self._kwargs
    ) as visible:
      save = visible.name
    
    os.replace(tmp.name, save)
    self.name = save
  
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
  
  def __exit__(self, exc, val, tb):
    self.close()
  
  def close(self):
    self.__closer()
  
  @property
  def name(self):
    try:
      return self.__wrapper.name
    except AttributeError:
      return self.__wrapper.tmp.name
  
  @property
  def save(self):
    return self.__wrapper.save
  
  @save.setter
  def save(self, value):
    self.__wrapper.save = value