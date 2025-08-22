import tkinter as tk
from tkinter import ttk

from .. import gui
from . import embed as gui_embed

TITLE = 'Calibrate'
RESIZABLE = True
SIZE = (520, 500)

DEFAULT_SCALE_VALUE = 100

MASTER_LIMIT = 0.00001
MASTER_CENTER = 100.0


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


def _undoable_scales(scales, master_scale, text, reset_button, undooptions):
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
  oldmasters = oldvalues
  
  for scale in scales.values():
    defaults[scale] = DEFAULT_SCALE_VALUE
    oldvalues[scale] = scale.get()
    
    # this bindtag must be on the end
    # so that we don't swallow all events before the text gets them
    scale.bindtags(scale.bindtags() + (bindtag,))
  
  def set_(widget, newvalue):
    oldvalues[widget] = newvalue
    
    # the value of MASTER_LIMIT is such that if the master scale is
    # set to zero, then another scale has its value changed from zero
    # to any non-zero number, it will jump to the highest possible
    # percentage (200%) representable by the scales at any other master value
    oldmasters[widget] = round(newvalue / max(
      MASTER_LIMIT,
      master_scale.get() / MASTER_CENTER
    ))
  
  def revert(widget, newvalue):
    # look at and focus the widget so the user notices what's just changed
    text.see(widget.master)
    widget.focus_set()
    
    widget.set(newvalue)
    set_(widget, newvalue)
  
  def data(e):
    widget = e.widget
    
    # don't do anything if the value hasn't changed
    oldvalue = oldvalues[widget]
    newvalue = widget.get()
    if oldvalue == newvalue: return
    
    print(f'Undo scale save {widget} {newvalue} {oldvalue}')
    
    undooptions(
      (revert, widget, oldvalue),
      (revert, widget, newvalue)
    )
    
    set_(widget, newvalue)
  
  # focus out is caught in case a widget gets a key press then loses focus before key release
  gui.bind_truekey_widget(text, class_=bindtag, release=data)
  
  for name in NAMES:
    text.bind_class(bindtag, name, data)
  
  def master(scale):
    def set_(newvalue, newmasters):
      for scale, newmaster in newmasters.items():
        scale.set(round(newmaster * (newvalue / MASTER_CENTER)))
    
    command = scale['command']
    
    def call_command(*args):
      set_(scale.get(), oldmasters)
      return scale.tk.call(command, *args)
    
    scale['command'] = call_command
    
    oldvalue = scale.get()
    
    def revert(newvalue, newvalues, newmasters):
      nonlocal oldvalue
      nonlocal oldvalues
      nonlocal oldmasters
      
      scale.set(newvalue)
      oldvalue = newvalue
      
      set_(newvalue, newmasters)
      
      oldvalues = newvalues.copy()
      oldmasters = newmasters.copy()
    
    def data(e):
      nonlocal oldvalue
      nonlocal oldvalues
      
      newvalue = scale.get()
      if oldvalue == newvalue: return
      
      print(f'Undo master scale save {scale} {newvalue} {oldvalue}')
      
      # oldmasters must be copied because it could be mutated
      # by the normal revert function still
      newvalues = {s: s.get() for s in oldvalues.keys()}
      newmasters = oldmasters.copy()
      
      undooptions(
        (revert, oldvalue, oldvalues, newmasters),
        (revert, newvalue, newvalues, newmasters)
      )
      
      oldvalue = newvalue
      oldvalues = newvalues.copy()
    
    gui.bind_truekey_widget(scale, release=data)
    
    for name in NAMES:
      scale.bind(name, data)
  
  master(master_scale)
  
  def reset():
    # it's okay to use a dictionary as a default here
    # because we won't ever be mutating it
    def revert(newvalues=defaults, newmasters=defaults, master_oldvalue=DEFAULT_SCALE_VALUE):
      nonlocal oldvalues
      nonlocal oldmasters
      
      for scale, newvalue in newvalues.items():
        scale.set(newvalue)
      
      # we must copy this here so we don't mutate a redo state
      oldvalues = newvalues.copy()
      oldmasters = newmasters.copy()
      master_scale.set(master_oldvalue)
    
    # the oldvalues must be copied when turned into an undooption
    # because they get changed as the scales are set
    # if we didn't copy, then as we set the scales, they'd mutate the undo state (bad!)
    undooptions(
      (revert, oldvalues.copy(), oldmasters.copy(), master_scale.get()),
      (revert,)
    )
    
    revert()
  
  reset_button['command'] = reset


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
  
  # TODO: recentre button
  master_scale = gui.make_scale(
    scale_frame,
    name='Master',
    to=200
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
  
  _undoable_scales(scales, master_scale, calibration_text, reset_button, undooptions)
  
  gui.set_modal_window(window)