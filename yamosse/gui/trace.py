from .. import gui

class Trace:
  def __init__(self, widget, operation, callback):
    # this class is intended to ensure that widgets remove their
    # associated variable from a trace when they cease to exist
    # the trace should be removed if this object goes out of scope
    # or if the widget is destroyed
    # (and thus the command registered on it ceases to exist)
    tk = widget.tk
    cbname = widget.register(callback)
    variable = widget['variable']
    
    self._tk = tk
    self._operation = operation
    self._cbname = cbname
    self._variable = variable
    
    # this event fires UNDER the call to destroy() on widgets
    # as if the event was generated with when='now'
    # that is to say, there is no a window of time
    # during which destroy() has been called but the event is
    # waiting in the event loop before it can trigger
    # that means this in effect is like monkey patching the destroy() function
    # and is safe to use as a "here are extra things you should do on destroy()"
    # bindtag_window is used in case this is a window
    # it is safe, albeit slightly redundant, to use on other widgets
    widget.bind_class(gui.bindtag_window(widget),
      '<Destroy>', lambda e: self.__del__(), add=True)
    
    # we manually call trace add/remove here, because
    # in all likelihood the variable is a string variable name
    tk.call('trace', 'add', 'variable',
      variable, operation, cbname)
  
  def __del__(self):
    tk = self._tk
    operation = self._operation
    cbname = self._cbname
    
    # in case this is called multiple times, we delete the variable
    # so that the trace will only ever be removed one time
    try:
      variable = self._variable
    except AttributeError:
      pass
    else:
      tk.call('trace', 'remove', 'variable',
        variable, operation, cbname)
      
      del self._variable
    
    # release any other references we're holding onto
    self._tk = None
    self._operation = None
    self._cbname = None
  
  @property
  def variable(self):
    return self._variable