import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod

from .. import gui
from . import embed as gui_embed

TITLE = 'Calibrate'
RESIZABLE = True
SIZE = (520, 500)

FROM_SCALE_VALUE = 0.00001
DEFAULT_SCALE_VALUE = 100.0
TO_SCALE_VALUE = 200.0

FROM_SCALE_ROUND = round(FROM_SCALE_VALUE)
DEFAULT_SCALE_ROUND = round(DEFAULT_SCALE_VALUE)
TO_SCALE_ROUND = round(TO_SCALE_VALUE)


class _UndoableWidget(ABC):
  __slots__ = ('_undooptions',)
  
  def __init__(self, undooptions):
    self._undooptions = undooptions
  
  @abstractmethod
  def revert(self, *args, focus=True):
    pass


class _UndoableScale(_UndoableWidget):
  def bind(self, widget, class_):
    data = self.data
    
    gui.bind_truekey_widget(widget, class_=class_, release=data, add=True)
    
    # focus out is caught in case a widget gets a key press
    # then loses focus before key release
    for sequence in ('<ButtonRelease>', '<FocusOut>'):
      widget.bind_class(class_, sequence, data, add=True)
    
    # this must use a double button *release* specifically
    # so that the event handler can compare the old/new value
    # but for spacebar it's just a standard key event
    # (same as pressing a button)
    for sequence in ('<Double-ButtonRelease>', '<Key-space>'):
      widget.bind_class(
        class_,
        sequence,
        lambda e: data(e, recenter=True),
        add=True
      )
  
  @abstractmethod
  def revert(self, *args, focus=True):
    pass
  
  @abstractmethod
  def data(self, e, recenter=False):
    widget = e.widget
    
    oldvalue = self._old(widget)
    newvalue = float(widget.get())
    
    if recenter:
      # disallow double clicking on the bar area to recentre
      # it should only be possible by double clicking the squeezy-grabber thing
      # so it doesn't interfere with people clicking on the bar to increment by one
      if oldvalue != newvalue:
        raise ValueError('oldvalue must equal newvalue')
      
      newvalue = DEFAULT_SCALE_VALUE
    
    if oldvalue == newvalue:
      raise ValueError('oldvalue must not equal newvalue')
    
    return widget, newvalue, oldvalue, recenter
  
  @abstractmethod
  def show(self, *args, **kwargs):
    pass
  
  @staticmethod
  def values(scales):
    return {s: float(s.get()) for s in scales}
  
  @abstractmethod
  def _old(self, widget):
    pass


class _UndoableMaster(_UndoableScale):
  __slots__ = ('_tk', '_scale', '_command', 'oldvalues', 'oldvalue', 'calibration')
  
  def __init__(self, undooptions, scale, calibration):
    super().__init__(undooptions)
    
    self._tk = scale.tk
    self._scale = scale
    self._command = scale['command']
    scale['command'] = self._master
    
    # editing our own oldvalues should never affect the calibration's oldvalues
    # so to be safe, we copy here
    self.oldvalues = calibration.oldvalues.copy()
    self.oldvalue = float(scale.get())
    self.bind(scale, scale)
    
    self.calibration = calibration
  
  def revert(self, *args, focus=True):
    calibration_newvalues, newvalues, newvalue = args
    
    # we must copy this here so we don't mutate a redo state
    self.calibration.oldvalues = calibration_newvalues.copy()
    self.oldvalues = newvalues.copy()
    self.oldvalue = newvalue
    
    # this must happen last, invokes self._master function
    scale = self._scale
    
    if focus:
      scale.focus_set()
    
    scale.set(newvalue)
  
  def data(self, e, recenter=False):
    try:
      widget, newvalue, oldvalue, recenter = super().data(e, recenter=recenter)
    except ValueError:
      return None
    
    print(f'Undo master scale save {widget} {newvalue} {oldvalue} {recenter}')
    
    calibration = self.calibration
    
    oldvalues = self.oldvalues
    calibration_oldvalues = calibration.oldvalues
    
    # if recentring, use the calibration oldvalues so that
    # the master scale moves independently of them
    # (copy calibration.oldvalues so we don't mutate oldvalues not belonging to us)
    # otherwise, use our previous oldvalues so we continue
    # to scale them proportionally
    newvalues = calibration_oldvalues.copy() if recenter else oldvalues
    calibration_newvalues = self.get_calibration_newvalues(
      widgets=oldvalues, newvalue=newvalue)
    
    # I know, I know. Four separate copies, is it really necessary?
    # *Trust me.* Don't remove the .copy() calls. Down that path lies madness
    revert = self.revert
    
    self._undooptions(
      (revert, calibration_oldvalues.copy(), oldvalues.copy(), oldvalue),
      (revert, calibration_newvalues.copy(), newvalues.copy(), newvalue)
    )
    
    calibration.oldvalues = calibration_newvalues
    self.oldvalues = newvalues
    self.oldvalue = newvalue
    
    if recenter:
      self._scale.set(newvalue)
    
    return widget, newvalue, oldvalue, recenter
  
  def show(self, *args, **kwargs):
    calibration_newvalues = self.get_calibration_newvalues(*args, **kwargs)
    
    for widget, calibration_newvalue in calibration_newvalues.items():
      widget.set(calibration_newvalue)
  
  def value(self):
    return float(self._scale.get())
  
  def get_calibration_newvalues(self, widgets=None, newvalue=None):
    # by default, only use the scales that are within a visible window
    if widgets is None:
      widgets = self.calibration.scales
    
    # get the current calibration scale values
    # after clicking and dragging the master scale
    # this must be representative of the actual numbers on the visible scales
    # which is why we cap it to the TO_SCALE_VALUE
    reciprocal = self._reciprocal(newvalue)
    
    return {
      w: min(
        round(self.oldvalues[w] * reciprocal),
        TO_SCALE_VALUE
      ) for w in widgets
    }
  
  def set_oldvalue(self, widget, newvalue):
    # mirror the calibration scale value so
    # the master scale moves it proportionally to the others correctly
    # this is intentionally not capped to the TO_SCALE_VALUE
    # (numbers in here may get very large!)
    self.oldvalues[widget] = round(newvalue / self._reciprocal())
  
  def _old(self, widget):
    return self.oldvalue
  
  def _reciprocal(self, value=None):
    # the value of FROM_SCALE_VALUE is such that if the master scale is
    # set to zero, then another scale has its value changed from zero
    # to any non-zero number, it will jump to the highest possible
    # percentage (200%) representable by the scales at any other master value
    # but return to its original value if the master slider is moved back to zero
    if value is None:
      value = self.value()
    
    return max(
      value / DEFAULT_SCALE_VALUE,
      FROM_SCALE_VALUE
    )
  
  def _master(self, text, *args):
    self.show(newvalue=float(text))
    
    command = self._command
    
    if not command:
      return ''
    
    return self._tk.call(command, text, *args)


# There are a couple known issues with this:
# -hitting Ctrl+Z while clicking and dragging a scale undoes other scales
#   while still editing the current one. The ideal is that undo is disabled
#   when you're in the middle of a click and drag.
# -if you tab into one of the scales and hold the up/down arrow keys to edit it
#   then simultaneously click the Undo button, you can undo the current widget while
#   it's still navigating, clobbering the Redo stack in the process. The ideal would
#   be that if you have any key held on a focused scale, you can't undo, but the problem is
#   this should obviously not apply to Ctrl+Z/Ctrl+Y itself, which needs to work
#   even if a scale is focused. Thing is I don't want to make the assumption in this code
#   that the arrow keys are the only editing hotkeys, nor do I want to assume
#   that Ctrl+Z/Ctrl+Y are the only undo hotkeys. So really it should only undo if... when???
# I anticipate that both of these problems could be solved in the same way/with the same
# simple solution, which I just can't think of at the moment. It will obviously involve
# capturing ButtonPress/KeyPress events to know when you're "clicked in," but it's the
# exceptions to the rule that make things difficult. I did think of using variable tracing,
# but that wouldn't catch if you've clicked a scale but not actually moved it yet, plus
# it'd also trip when we edit the scales here in code, via undoing/redoing. So, I don't know...
class _UndoableCalibration(_UndoableScale):
  __slots__ = ('_tk', '_text', 'oldvalues', 'scales', 'master', 'reset')
  
  def __init__(self, undooptions, text, scales, master_scale, reset_button):
    super().__init__(undooptions)
    
    self._tk = text.tk
    self._text = text
    
    # the calibration oldvalues should contain the "true" state of the scales
    # at all times. It should never contain numbers larger than TO_SCALE_VALUE (200.0)
    # if it does, it probably leaked out of UndoableMaster which is a bug
    oldvalues = self.values(scales.values())
    self.oldvalues = oldvalues
    self.scales = oldvalues
    
    # this bindtag must be on the end
    # so that we don't swallow all events before the text gets them
    text_bindtag = gui.bindtag(text)
    
    for scale in oldvalues:
      scale.bindtags(scale.bindtags() + (text_bindtag,))
    
    # we need to update the list of visible scales
    # in basically any circumstance that would normally cause
    # the scrollbar appearance to change
    # so here we add our own scrollcommands
    for scrollcommand in (tk.X, tk.Y):
      scrollcommand = ''.join((scrollcommand, 'scrollcommand'))
      
      command = text[scrollcommand]
      if not command: continue
      
      def scroll(*args, command=command): return self._scrollcommand(command, *args)
      text[scrollcommand] = scroll
    
    self.bind(text, text_bindtag)
    
    self.master = _UndoableMaster(undooptions, master_scale, self)
    self.reset = _UndoableReset(undooptions, reset_button, self)
  
  def revert(self, *args, focus=True):
    widget, newvalue = args
    
    # look at and focus the widget so the user notices what's just changed
    self._text.see(widget.master)
    
    if focus:
      widget.focus_set()
    
    widget.set(newvalue)
    
    self.show(widget, newvalue)
  
  def data(self, e, recenter=False):
    try:
      widget, newvalue, oldvalue, recenter = super().data(e, recenter=recenter)
    except ValueError:
      return None
    
    print(f'Undo calibration scale save {widget} {newvalue} {oldvalue} {recenter}')
    
    revert = self.revert
    
    self._undooptions(
      (revert, widget, oldvalue),
      (revert, widget, newvalue)
    )
    
    if recenter:
      widget.set(newvalue)
    
    self.show(widget, newvalue)
    return widget, newvalue, oldvalue, recenter
  
  def show(self, *args, **kwargs):
    widget, newvalue = args
    
    self.oldvalues[widget] = newvalue
    self.master.set_oldvalue(widget, newvalue)
  
  def _old(self, widget):
    return self.oldvalues[widget]
  
  def _scrollcommand(self, command, *args):
    text = self._text
    
    # get all windows currently visible on screen
    windows = [text.nametowidget(d[1]) for d in text.dump(
      '@0,0', # top left
      '@%d,%d + 1 indices' % (text.winfo_width(), text.winfo_height()), # bottom right
      window=True
    )]
    
    # get the scales in those windows
    self.scales = [s for s in self.oldvalues if s.master in windows]
    
    # we need to show the master again in case the user scrolls the widget
    # while editing the master (like by pressing the arrow keys)
    self.master.show()
    return self._tk.call(command, *args)


class _UndoableReset(_UndoableWidget):
  __slots__ = ('_button', 'oldvalues', 'calibration')
  
  def __init__(self, undooptions, button, calibration):
    super().__init__(undooptions)
    
    self._button = button
    button['command'] = self._reset
    
    self.oldvalues = {s: DEFAULT_SCALE_VALUE for s in calibration.oldvalues}
    self.calibration = calibration
  
  def revert(self, *args, focus=True):
    ARGS_LEN = 3
    
    args += (None,) * ARGS_LEN
    calibration_newvalues, master_newvalues, master_newvalue = args[:ARGS_LEN]
    
    oldvalues = self.oldvalues
    
    if calibration_newvalues is None:
      calibration_newvalues = oldvalues
    
    if master_newvalues is None:
      master_newvalues = oldvalues
    
    if master_newvalue is None:
      master_newvalue = DEFAULT_SCALE_VALUE
    
    if focus:
      self._button.focus_set()
    
    # we don't need to revert the calibration directly
    # reverting its master will have the side effect of reverting it anyway
    self.calibration.master.revert(
      calibration_newvalues,
      master_newvalues,
      master_newvalue,
      focus=False
    )
  
  def _reset(self):
    calibration = self.calibration
    master = calibration.master
    
    revert = self.revert
    
    # the oldvalues must be copied when turned into an undooption
    # because they get changed as the scales are set
    # if we didn't copy, then as we set the scales, they'd mutate the undo state (bad!)
    self._undooptions(
      (
        revert,
        calibration.oldvalues.copy(),
        master.oldvalues.copy(),
        master.value()
      ),
      
      (revert,)
    )
    
    revert(focus=False)


def make_footer(frame, ok, cancel):
  frame.columnconfigure(1, weight=1)
  
  undoable_frame = ttk.Frame(frame)
  undoable_frame.grid(row=0, column=0, sticky=tk.W)
  undooptions = gui.make_undoable(undoable_frame).undooptions
  
  ok_button = ttk.Button(frame, text='OK', underline=0, command=ok, default=tk.ACTIVE)
  ok_button.grid(row=0, column=2, sticky=tk.E, padx=gui.PADX_QW)
  
  cancel_button = ttk.Button(frame, text='Cancel', underline=0, command=cancel)
  cancel_button.grid(row=0, column=3, sticky=tk.E, padx=gui.PADX_QW)
  
  reset_button = ttk.Button(frame, text='Reset', underline=0)
  reset_button.grid(row=0, column=4, sticky=tk.E, padx=gui.PADX_QW)
  
  gui.bind_buttons_window(
    frame.winfo_toplevel(),
    ok_button=ok_button,
    cancel_button=cancel_button
  )
  
  for button in (ok_button, cancel_button, reset_button):
    gui.enable_traversal_button(button)
  
  return undooptions, reset_button


def make_calibrate(frame, variables, class_names, attached):
  BORDERWIDTH = 4
  
  window = frame.master
  parent = window.master
  
  gui.customize_window(window, TITLE, resizable=RESIZABLE, size=SIZE,
    location=gui.location_center_window(parent, SIZE))
  
  gui.minsize_window(window)
  
  frame.rowconfigure(1, weight=1) # make calibration frame vertically resizable
  frame.columnconfigure(0, weight=1) # make calibration frame horizontally resizable
  
  master_frame = ttk.Frame(frame, borderwidth=BORDERWIDTH)
  master_frame.grid(row=0, sticky=tk.EW)
  master_scale = gui.make_scale(master_frame, name='Master',
    from_=FROM_SCALE_ROUND, to=TO_SCALE_ROUND).middle
  
  master_scale.set(DEFAULT_SCALE_ROUND)
  
  master_frame.columnconfigure(0, weight=2, uniform='scale_column')
  master_frame.columnconfigure(1, weight=1, uniform='scale_column')
  
  calibration_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=BORDERWIDTH)
  calibration_frame.grid(row=1, sticky=tk.NSEW)
  calibration_text = gui.make_text(calibration_frame,
    font=('TkDefaultFont', 24)).middle[0]
  
  gui_embed.text_embed(calibration_text)
  
  # put in 100% as defaults if the calibration is empty/too short
  calibration_variable = variables['calibration']
  
  calibration_variable += (
    [DEFAULT_SCALE_ROUND]
    * (len(class_names) - len(calibration_variable))
  )
  
  scales = {}
  
  for cid, values in attached.items():
    number, class_name = values
    
    scale_frame = ttk.Frame(calibration_text)
    
    scale = gui.make_scale(
      scale_frame,
      name='%d. %s' % (int(number), class_name),
      from_=FROM_SCALE_ROUND, to=TO_SCALE_ROUND
    ).middle
    
    scale.set(int(calibration_variable[cid]))
    scales[cid] = scale
    
    scale_frame.columnconfigure(0, weight=2, uniform='scale_column')
    scale_frame.columnconfigure(1, weight=1, uniform='scale_column')
    
    gui_embed.insert_embed(calibration_text, scale_frame)
  
  footer_frame = ttk.Frame(frame)
  footer_frame.grid(row=2, sticky=tk.EW, pady=gui.PADY_N)
  
  undoable_calibration = None
  
  def ok():
    # we can't just get the values of all the scales here
    # because their values aren't updated if they aren't on screen
    # oldvalues is the true arbiter of the state they're meant to be in
    oldvalues = undoable_calibration.oldvalues
    
    for cid in attached:
      calibration_variable[cid] = int(oldvalues[scales[cid]])
    
    gui.release_modal_window(window)
  
  undooptions, reset_button = make_footer(
    footer_frame,
    ok,
    lambda: gui.release_modal_window(window)
  )
  
  undoable_calibration = _UndoableCalibration(
    undooptions,
    calibration_text,
    scales,
    master_scale,
    reset_button
  )
  
  gui.set_modal_window(window)