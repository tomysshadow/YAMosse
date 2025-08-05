import tkinter as tk
from tkinter import ttk

from .. import gui
from . import embed as gui_embed

TITLE = 'Calibrate'
RESIZABLE = True
SIZE = (520, 500)

DEFAULT_SCALE_VALUE = 100


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


def _undoable_scales(scales, text, reset_button, undooptions):
  bindtag = gui.bindtag_for_object(text)
  
  defaults = {}
  oldvalues = {}
  
  for scale in scales:
    defaults[scale] = DEFAULT_SCALE_VALUE
    oldvalues[scale] = scale.get()
    
    # this bindtag must be on the end
    # so that we don't swallow all events before the text gets them
    scale.bindtags(scale.bindtags() + (bindtag,))
  
  get_dragging, set_dragging, get_navigating, set_navigating, doing = _states()
  
  def revert(widget, newvalue):
    # don't Undo if the user is doing something
    if doing(): raise gui.UndoError
    
    text.see(widget.master)
    widget.focus_set()
    
    widget.set(newvalue)
    oldvalues[widget] = newvalue
  
  def data(e):
    # don't do anything in the middle of a click and drag
    if get_dragging(): return
    
    widget = e.widget
    
    # don't do anything if the value hasn't changed
    oldvalue = oldvalues[widget]
    newvalue = widget.get()
    if oldvalue == newvalue: return
    
    print(f'Undo scale save {widget} {newvalue} {oldvalue}')
    
    undooptions((revert, widget, oldvalue), (revert, widget, newvalue))
    oldvalues[widget] = newvalue
  
  # focus out is caught in case a widget gets a key press then loses focus before key release
  text.bind_class(bindtag, '<ButtonPress>', lambda e: set_dragging(True))
  text.bind_class(bindtag, '<ButtonRelease>', lambda e: set_dragging(False))
  text.bind_class(bindtag, '<ButtonRelease>', data, add=True)
  text.bind_class(bindtag, '<FocusOut>', data)
  
  gui.bind_truekey_widget(text, class_=bindtag,
    press=lambda e: set_navigating(e.widget), release=data)
  
  gui.bind_truekey_widget(text, class_='all',
    release=lambda e: set_navigating(None))
  
  def reset():
    # possible if the user uses Alt + R and Space to hit the button
    # we're not worried about navigating here, because
    # it'd be impossible to cause a reset without focusing out
    # which will "commit" the undo state correctly before the reset
    if get_dragging(): return
    
    # it's okay to use a dictionary as a default here
    # because we won't ever be mutating it
    def revert(newvalues=defaults, undo=True):
      nonlocal oldvalues
      
      # don't Undo if the user is doing something
      if undo and doing(): raise gui.UndoError
      
      for scale, newvalue in newvalues.items():
        scale.set(newvalue)
      
      # we must copy this here so we don't mutate a redo state
      oldvalues = newvalues.copy()
    
    # the oldvalues must be copied when turned into an undooption
    # because they get changed as the scales are set
    # if we didn't copy, then as we set the scales, they'd mutate the undo state (bad!)
    undooptions((revert, oldvalues.copy()), (revert,))
    revert(undo=False)
  
  reset_button['command'] = reset


def make_calibrate(frame, variables, class_names):
  window = frame.master
  parent = window.master
  
  gui.customize_window(window, TITLE, resizable=RESIZABLE, size=SIZE,
    location=gui.location_center_window(parent, SIZE))
  
  frame.rowconfigure(0, weight=1) # make calibration frame vertically resizable
  frame.columnconfigure(0, weight=1) # make calibration frame horizontally resizable
  
  calibration_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=4)
  calibration_frame.grid(row=0, sticky=tk.NSEW)
  
  calibration_text = gui.make_text(calibration_frame, font=('TkDefaultFont', 24))[1][0]
  gui_embed.text_embed(calibration_text)
  
  # put in 100% as defaults if the calibration is empty/too short
  calibration_variable = variables['calibration']
  calibration_variable += [DEFAULT_SCALE_VALUE] * (len(class_names) - len(calibration_variable))
  
  number = 0
  scales = []
  
  for class_name, calibration in zip(class_names, calibration_variable):
    scale_frame = ttk.Frame(calibration_text)
    
    scale = gui.make_scale(
      scale_frame,
      name='%d. %s' % (number := number + 1, class_name),
      to=200
    )[1]
    
    scale.set(int(calibration))
    scales.append(scale)
    
    scale_frame.columnconfigure(0, weight=2, uniform='class_column')
    scale_frame.columnconfigure(1, weight=1, uniform='class_column')
    
    gui_embed.insert_embed(calibration_text, scale_frame)
  
  footer_frame = ttk.Frame(frame)
  footer_frame.grid(row=1, sticky=tk.EW, pady=gui.PADY_N)
  
  def ok():
    variables['calibration'] = [int(s.get()) for s in scales]
    gui.release_modal_window(window)
  
  undooptions, reset_button = make_footer(
    footer_frame,
    ok,
    lambda: gui.release_modal_window(window)
  )
  
  _undoable_scales(scales, calibration_text, reset_button, undooptions)
  
  gui.set_modal_window(window)


def _states():
  dragging = False
  
  def get_dragging():
    return dragging
  
  def set_dragging(state):
    nonlocal dragging
    
    dragging = state
  
  navigating = None
  
  def get_navigating():
    return navigating
  
  def set_navigating(widget):
    nonlocal navigating
    
    navigating = widget
  
  def doing():
    if dragging: return True
    return navigating and not 'focus' in navigating.state()
  
  return get_dragging, set_dragging, get_navigating, set_navigating, doing