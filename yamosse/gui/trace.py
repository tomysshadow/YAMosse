class Trace:
  def __init__(self, widget, variable, operation, callback):
    # we manually call trace add/remove here
    # juuust in case we get passed a string variable name
    self._tk = widget.tk
    self._variable = variable
    self._operation = operation
    self._cbname = widget.register(callback)
    
    self._tk.call('trace', 'add', 'variable',
      variable, self._operation, self._cbname)
  
  def __del__(self):
    self._tk.call('trace', 'remove', 'variable',
      self._variable, self._operation, self._cbname)
  
  @property
  def variable(self):
    return self._variable