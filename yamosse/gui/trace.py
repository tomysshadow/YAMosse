import weakref

from .. import gui

class Trace:
  def __init__(self, widget, operation, callback):
    # this class is intended to ensure that widgets remove their
    # associated variable from a trace when they cease to exist
    # the trace should be removed if this object goes out of scope
    # (so that traces can be used in a "RAII" fashion)
    # or if the widget is destroyed
    # (and thus the command registered on it ceases to exist)
    tk = widget.tk
    variable = widget['variable']
    cbname = widget.register(callback)
    
    # this is created as a local variable
    # so we can use it in the event bound to the widget
    # without creating another reference to self
    # maybe that would have zero impact, but either way
    # it's just easier to keep track of in my head
    destroy = weakref.finalize(self, Trace.__finalize,
      tk, variable, operation, cbname)
    
    # this object should only ever be bound to one variable
    # swapping this to a different variable would defeat the point
    # so it's internal, with a getter only
    self._variable = variable
    self._destroy = destroy
    
    # this event fires UNDER the call to destroy() on widgets
    # as if the event was generated with when='now'
    # that is to say, there is no window of time
    # during which destroy() has been called but the event is
    # waiting in the event loop before it can trigger
    # that means this is in effect like monkey patching the destroy() function
    # and is safe to use as a "here are extra things you should do on destroy()"
    # bindtag_window is used in case this is a window
    # it is safe, albeit slightly redundant, to use on other widgets
    widget.bind_class(gui.bindtag_window(widget),
      '<Destroy>', lambda e: destroy(), add=True)
    
    # we manually call trace add/remove here, because
    # in all likelihood the variable is a string variable name
    tk.call('trace', 'add', 'variable',
      variable, operation, cbname)
  
  @classmethod
  @staticmethod
  def __finalize(tk, variable, operation, cbname):
    # this must be a class method so that we
    # don't create a circular reference for weakref
    tk.call('trace', 'remove', 'variable',
      variable, operation, cbname)
  
  @property
  def variable(self):
    return self._variable
  
  @property
  def destroy(self):
    return self._destroy
  
  def __enter__(self):
    return self
  
  def __exit__(self, *args, **kwargs):
    self.destroy()