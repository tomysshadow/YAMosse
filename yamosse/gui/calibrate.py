import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod

from .. import gui
from . import embed as gui_embed

TITLE = 'Calibrate'
RESIZABLE = True
SIZE = (520, 500)

DEFAULT_SCALE_VALUE = 100

MASTER_LIMIT = 0.00001
MASTER_CENTER = 100.0

class UndoableWidget(ABC):
  def __init__(self, undooptions):
    self._undooptions = undooptions
  
  @abstractmethod
  def revert(self, *args, focus=True):
    pass

class UndoableScale(UndoableWidget):
  @abstractmethod
  def revert(self, *args, focus=True):
    pass
  
  @abstractmethod
  def data(self, e):
    pass
  
  @abstractmethod
  def show(self, *args, **kwargs):
    pass
  
  @staticmethod
  def scalevalues(scales):
    return {s: float(s.get()) for s in scales}
  
  def bind(self, widget, class_):
    data = self.data
    
    gui.bind_truekey_widget(widget, class_=class_, release=data)
    
    # focus out is caught in case a widget gets a key press
    # then loses focus before key release
    for name in ('<ButtonRelease>', '<FocusOut>'):
      widget.bind_class(class_, name, data)

class UndoableMaster(UndoableScale):
  def __init__(self, undooptions, scale, calibration):
    super().__init__(undooptions)
    
    self._scale = scale
    self._tk = scale.tk
    self._command = scale['command']
    
    self.oldvalues = calibration.oldvalues
    self.oldvalue = float(scale.get())
    
    scale['command'] = self._master
    scale.bind('<Double-ButtonRelease>', lambda e: self.data(e, recenter=True))
    self.bind(scale, scale)
    
    self.calibration = calibration
  
  def revert(self, calibration_newvalues, newvalues, newvalue, focus=True):
    # we must copy this here so we don't mutate a redo state
    self.calibration.oldvalues = calibration_newvalues.copy()
    self.oldvalues = newvalues.copy()
    self.oldvalue = newvalue
    
    # this must happen last, invokes self._master function
    scale = self._scale
    if focus: scale.focus_set()
    scale.set(newvalue)
    
    # show all scales, not just the visible ones
    self.show(widgets=newvalues, newvalue=newvalue)
  
  def data(self, e, recenter=False):
    widget = e.widget
    
    oldvalue = self.oldvalue
    newvalue = float(widget.get())
    
    if oldvalue == newvalue and (not recenter or oldvalue == DEFAULT_SCALE_VALUE):
      return
    
    if recenter: newvalue = DEFAULT_SCALE_VALUE
    
    print(f'Undo master scale save {widget} {newvalue} {oldvalue} {recenter}')
    
    calibration = self.calibration
    calibration_oldvalues = calibration.oldvalues
    calibration_newvalues = self.scalevalues(calibration_oldvalues)
    
    # oldvalues must be copied if not recentring
    # because it could be mutated by the normal revert function still
    # it does not need to be copied in the recentre case
    # because in that case we will be replacing it with newvalues anyway
    oldvalues = self.oldvalues
    newvalues = self.scalevalues(oldvalues) if recenter else (oldvalues := oldvalues.copy())
    
    revert = self.revert
    
    self._undooptions(
      (revert, calibration_oldvalues, oldvalues, oldvalue),
      (revert, calibration_newvalues, newvalues, newvalue)
    )
    
    calibration.oldvalues = calibration_newvalues.copy()
    self.oldvalue = newvalue
    
    if recenter:
      # newvalues must be copied in this instance to avoid mutating the redo state
      self.oldvalues = newvalues.copy()
      self._scale.set(newvalue)
    
    self.show(widgets=newvalues, newvalue=newvalue)
  
  def show(self, widgets=None, newvalue=None):
    oldvalues = self.oldvalues
    
    # by default, only show the scales that are within a visible window
    if widgets is None:
      widgets = self.calibration.scales
    
    if newvalue is None:
      newvalue = self.value()
    
    multiplier = float(newvalue) / MASTER_CENTER
    
    for widget in widgets:
      widget.set(round(oldvalues[widget] * multiplier))
  
  def calibrate(self, widget, newvalue):
    # the value of MASTER_LIMIT is such that if the master scale is
    # set to zero, then another scale has its value changed from zero
    # to any non-zero number, it will jump to the highest possible
    # percentage (200%) representable by the scales at any other master value
    self.oldvalues[widget] = round(
      newvalue / max(
        MASTER_LIMIT,
        self.value() / MASTER_CENTER
      )
    )
  
  def value(self):
    return float(self._scale.get())
  
  def _master(self, text, *args):
    self.show(newvalue=text)
    
    command = self._command
    if not command: return
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
class UndoableCalibration(UndoableScale):
  def __init__(self, undooptions, text, scales, master_scale, reset_button):
    super().__init__(undooptions)
    
    self._text = text
    self._tk = text.tk
    
    oldvalues = self.scalevalues(scales.values())
    self.oldvalues = oldvalues
    self.scales = oldvalues
    
    # this bindtag must be on the end
    # so that we don't swallow all events before the text gets them
    bindtag = gui.bindtag(text)
    
    for scale in oldvalues:
      scale.bindtags(scale.bindtags() + (bindtag,))
    
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
    
    self.bind(text, bindtag)
    
    self.master = UndoableMaster(undooptions, master_scale, self)
    self.reset = UndoableReset(undooptions, reset_button, self)
  
  def revert(self, widget, newvalue, focus=True):
    # look at and focus the widget so the user notices what's just changed
    self._text.see(widget.master)
    if focus: widget.focus_set()
    widget.set(newvalue)
    
    self.show(widget, newvalue)
  
  def data(self, e):
    widget = e.widget
    
    # don't do anything if the value hasn't changed
    oldvalue = self.oldvalues[widget]
    newvalue = float(widget.get())
    if oldvalue == newvalue: return
    
    print(f'Undo calibration scale save {widget} {newvalue} {oldvalue}')
    
    revert = self.revert
    
    self._undooptions(
      (revert, widget, oldvalue),
      (revert, widget, newvalue)
    )
    
    self.show(widget, newvalue)
  
  def show(self, widget, newvalue):
    self.oldvalues[widget] = newvalue
    self.master.calibrate(widget, newvalue)
  
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


class UndoableReset(UndoableWidget):
  def __init__(self, undooptions, button, calibration):
    super().__init__(undooptions)
    
    self._button = button
    
    self.oldvalues = {s: DEFAULT_SCALE_VALUE for s in calibration.oldvalues}
    
    button['command'] = self._reset
    
    self.calibration = calibration
  
  def revert(
    self,
    calibration_newvalues=None,
    master_newvalues=None,
    master_newvalue=DEFAULT_SCALE_VALUE,
    focus=True
  ):
    oldvalues = self.oldvalues
    
    if calibration_newvalues is None: calibration_newvalues = oldvalues
    if master_newvalues is None: master_newvalues = oldvalues
    
    if focus: self._button.focus_set()
    
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
  undooptions = gui.make_undoable(undoable_frame)[0]
  
  ok_button = ttk.Button(frame, text='OK', underline=0, command=ok, default=tk.ACTIVE)
  ok_button.grid(row=0, column=2, sticky=tk.E, padx=gui.PADX_QW)
  
  cancel_button = ttk.Button(frame, text='Cancel', underline=0, command=cancel)
  cancel_button.grid(row=0, column=3, sticky=tk.E, padx=gui.PADX_QW)
  
  reset_button = ttk.Button(frame, text='Reset', underline=0)
  reset_button.grid(row=0, column=4, sticky=tk.E, padx=gui.PADX_QW)
  
  gui.bind_buttons_window(frame.winfo_toplevel(), ok_button=ok_button, cancel_button=cancel_button)
  
  for button in (ok_button, cancel_button, reset_button):
    gui.enable_traversal_button(button)
  
  return undooptions, reset_button


def make_calibrate(frame, variables, class_names, attached):
  BORDERWIDTH = 4
  
  window = frame.master
  parent = window.master
  
  gui.customize_window(window, TITLE, resizable=RESIZABLE, size=SIZE,
    location=gui.location_center_window(parent, SIZE))
  
  frame.rowconfigure(1, weight=1) # make calibration frame vertically resizable
  frame.columnconfigure(0, weight=1) # make calibration frame horizontally resizable
  
  master_frame = ttk.Frame(frame, borderwidth=BORDERWIDTH)
  master_frame.grid(row=0, sticky=tk.EW)
  
  master_scale = gui.make_scale(master_frame, name='Master', to=200)[1]
  master_scale.set(DEFAULT_SCALE_VALUE)
  
  master_frame.columnconfigure(0, weight=2, uniform='class_column')
  master_frame.columnconfigure(1, weight=1, uniform='class_column')
  
  calibration_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=BORDERWIDTH)
  calibration_frame.grid(row=1, sticky=tk.NSEW)
  calibration_text = gui.make_text(calibration_frame, font=('TkDefaultFont', 24))[1][0]
  gui_embed.text_embed(calibration_text)
  
  # put in 100% as defaults if the calibration is empty/too short
  calibration_variable = variables['calibration']
  
  calibration_variable += (
    [DEFAULT_SCALE_VALUE]
    * (len(class_names) - len(calibration_variable))
  )
  
  scales = {}
  
  for cid, values in attached.items():
    number, class_name = values
    
    scale_frame = ttk.Frame(calibration_text)
    
    scale = gui.make_scale(
      scale_frame,
      name='%d. %s' % (int(number), class_name),
      to=200
    )[1]
    
    scale.set(int(calibration_variable[cid]))
    scales[cid] = scale
    
    scale_frame.columnconfigure(0, weight=2, uniform='class_column')
    scale_frame.columnconfigure(1, weight=1, uniform='class_column')
    
    gui_embed.insert_embed(calibration_text, scale_frame)
  
  footer_frame = ttk.Frame(frame)
  footer_frame.grid(row=2, sticky=tk.EW, pady=gui.PADY_N)
  
  def ok():
    for cid in attached:
      calibration_variable[cid] = int(scales[cid].get())
    
    gui.release_modal_window(window)
  
  undooptions, reset_button = make_footer(
    footer_frame,
    ok,
    lambda: gui.release_modal_window(window)
  )
  
  undoable_calibration = UndoableCalibration(
    undooptions,
    calibration_text,
    scales,
    master_scale,
    reset_button
  )
  
  gui.set_modal_window(window)