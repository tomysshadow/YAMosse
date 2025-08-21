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


def _undoable_scales(scales, master_scale_variable, text, reset_button, undooptions):
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
  NAMES = ('<ButtonRelease>', '<FocusOut>')
  
  bindtag = gui.bindtag(text)
  
  defaults = {}
  oldvalues = {}
  
  for scale in scales.values():
    defaults[scale] = DEFAULT_SCALE_VALUE
    oldvalues[scale] = scale.get()
    
    # this bindtag must be on the end
    # so that we don't swallow all events before the text gets them
    scale.bindtags(scale.bindtags() + (bindtag,))
  
  master_scale, master_variable = master_scale_variable
  master_oldvalues = oldvalues
  
  def mastervalue(widget, newvalue):
    oldvalues[widget] = newvalue
    
    master_value = (master_variable.get() / 100.0)
    if master_value: newvalue = round(newvalue / master_value)
    
    master_oldvalues[widget] = newvalue
  
  def revert(widget, newvalue):
    # look at and focus the widget so the user notices what's just changed
    text.see(widget.master)
    widget.focus_set()
    
    widget.set(newvalue)
    mastervalue(widget, newvalue)
  
  def data(e):
    widget = e.widget
    
    # don't do anything if the value hasn't changed
    oldvalue = oldvalues[widget]
    newvalue = widget.get()
    if oldvalue == newvalue: return
    
    print(f'Undo scale save {widget} {newvalue} {oldvalue}')
    
    undooptions((revert, widget, oldvalue), (revert, widget, newvalue))
    mastervalue(widget, newvalue)
  
  # focus out is caught in case a widget gets a key press then loses focus before key release
  gui.bind_truekey_widget(text, class_=bindtag, release=data)
  
  for name in NAMES:
    text.bind_class(bindtag, name, data)
  
  def master():
    def set_(master_values, value):
      for scale, master_value in master_values.items():
        scale.set(round(master_value * (value / 100.0)))
    
    oldvalue = master_variable.get()
    
    master_variable.trace('w',
      lambda *args, **kwargs: set_(master_oldvalues, master_variable.get()))
    
    def revert(newvalue, newvalues, master_newvalues):
      nonlocal oldvalue
      nonlocal oldvalues
      nonlocal master_oldvalues
      
      master_variable.set(newvalue)
      oldvalue = newvalue
      
      set_(master_newvalues, newvalue)
      
      oldvalues = newvalues.copy()
      master_oldvalues = master_newvalues.copy()
    
    def data(e):
      nonlocal oldvalue
      nonlocal oldvalues
      
      newvalue = master_variable.get()
      if oldvalue == newvalue: return
      
      print(f'Undo master scale save {master_scale} {newvalue} {oldvalue}')
      
      newvalues = {scale: scale.get() for scale in oldvalues.keys()}
      
      undooptions((revert, oldvalue, oldvalues.copy(), master_oldvalues.copy()),
        (revert, newvalue, newvalues.copy(), master_oldvalues.copy()))
      
      oldvalue = newvalue
      oldvalues = newvalues
    
    gui.bind_truekey_widget(master_scale, release=data)
    
    for name in NAMES:
      master_scale.bind(name, data)
  
  master()
  
  # TODO: add back reset code, just removed it so I could focus


def make_calibrate(frame, variables, class_names, attached):
  BORDERWIDTH = 4
  
  window = frame.master
  parent = window.master
  
  gui.customize_window(window, TITLE, resizable=RESIZABLE, size=SIZE,
    location=gui.location_center_window(parent, SIZE))
  
  frame.rowconfigure(0, weight=1) # make calibration frame vertically resizable
  frame.columnconfigure(0, weight=1) # make calibration frame horizontally resizable
  
  scale_frame = ttk.Frame(frame, borderwidth=BORDERWIDTH)
  scale_frame.grid(row=0, sticky=tk.NSEW)
  
  master_variable = tk.IntVar()
  
  master_scale = gui.make_scale(
    scale_frame,
    name='Master',
    to=200,
    variable=master_variable
  )[1]
  
  master_scale.set(DEFAULT_SCALE_VALUE)
  
  scale_frame.columnconfigure(0, weight=2, uniform='class_column')
  scale_frame.columnconfigure(1, weight=1, uniform='class_column')
  
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
  
  _undoable_scales(
    scales,
    (master_scale, master_variable),
    calibration_text,
    reset_button,
    undooptions
  )
  
  gui.set_modal_window(window)