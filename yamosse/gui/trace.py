class Trace:
  def __init__(self, widget, operation, callback):
    variable = widget['variable']
    
    self._tk = widget.tk
    self._variable = variable
    self._operation = operation
    self._cbname = widget.register(callback)
    
    # we manually call trace add/remove here
    # because in all likelihood the variable property is a string variable name
    self._tk.call('trace', 'add', 'variable',
      variable, self._operation, self._cbname)
  
  def __del__(self):
    self._tk.call('trace', 'remove', 'variable',
      self._variable, self._operation, self._cbname)
  
  @property
  def variable(self):
    return self._variable