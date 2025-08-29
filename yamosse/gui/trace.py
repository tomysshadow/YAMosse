from .. import gui

class Trace:
  def __init__(self, widget, operation, callback):
    # this class is intended to ensure that widgets remove their
    # associated variable from a trace when they cease to exist
    # the trace should be removed if this object goes out of scope
    # or if the widget is destroyed
    # (and thus the command registered on it ceases to exist)
    variable = widget['variable']
    
    self._variable = variable
    self._operation = operation
    self._cbname = widget.register(callback)
    self._tk = widget.tk
    
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
    
    # we manually call trace add/remove here,  because
    # in all likelihood the variable is a string variable name
    widget.tk.call('trace', 'add', 'variable',
      variable, self._operation, self._cbname)
  
  def __del__(self):
    operation = self._operation
    cbname = self._cbname
    tk = self._tk
    
    # in case this is called multiple times, we delete the variable
    # so that the trace will only ever be removed one time
    try:
      tk.call('trace', 'remove', 'variable',
        self._variable, operation, cbname)
    except AttributeError:
      pass
    else:
      del self._variable
    
    # release any other references we're holding onto
    self._operation = None
    self._cbname = None
    self._tk = None
  
  @property
  def variable(self):
    return self._variable