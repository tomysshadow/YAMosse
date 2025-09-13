from tempfile import NamedTemporaryFile
import os
import platform
import subprocess
import weakref

import yamosse.utils as yamosse_utils


class _HiddenFileWrapper:
  HIDDEN = '~'
  RETRIES = 10
  
  def __init__(self, *args, prefix='', **kwargs):
    self._system = platform.system()
    
    self._args = args
    self._prefix = prefix
    self._kwargs = kwargs
    
    self.save = False
    
    tmp = NamedTemporaryFile(
      *args,
      delete=False,
      prefix=yamosse_utils.str_ensureprefix(prefix, self.HIDDEN),
      **kwargs
    )
    
    self.tmp = tmp
    self.name = tmp.name
    self._hide(True)
  
  def close(self):
    tmp = self.tmp
    
    # I think this check is technically redundant
    # because we're called through a finalizer
    # but who knows
    if tmp.closed:
      return
    
    name = None
    src = tmp.name
    
    self._hide(False)
    tmp.close()
    
    try:
      if not self.save: return
      
      # first try stripping the tilde (~) off the current name
      head, tail = os.path.split(src)
      dest = os.path.join(head, tail.removeprefix(self.HIDDEN))
      
      for r in reversed(range(self.RETRIES)):
        try:
          # this should throw if a file with the same name gets created
          # before we can rename ours
          os.rename(src, dest)
        except OSError as exc:
          # raise exception if we exhausted all retries
          if not r: raise exc
          
          # generate a new visible name to use
          # that is guaranteed unique
          # I basically want mktemp here but that's deprecated
          # this is safe because rename will fail if the file exists
          with NamedTemporaryFile(
            *self._args,
            delete=True,
            prefix=self._prefix,
            **self._kwargs
          ) as tmp:
            dest = tmp.name
        else:
          name = dest
          break
    finally:
      self.name = name
      
      if name is None:
        os.unlink(src)
  
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
    return self.__wrapper.name
  
  @property
  def save(self):
    return self.__wrapper.save
  
  @save.setter
  def save(self, value):
    self.__wrapper.save = value