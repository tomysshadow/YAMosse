import tkinter as tk
from tkinter import ttk
from os import fsencode as fsenc

from .. import gui

TITLE = 'Calibrate'


def make_footer(frame, ok, cancel):
  frame.columnconfigure(1, weight=1)
  
  undoable_frame = ttk.Frame(frame)
  undoable_frame.grid(row=0, column=0, sticky=tk.W)
  
  gui.make_undoable(undoable_frame)
  
  ok_button = ttk.Button(frame, text='OK', underline=0, command=ok, default=tk.ACTIVE)
  ok_button.grid(row=0, column=2, sticky=tk.E, padx=gui.PADX_QW)
  
  cancel_button = ttk.Button(frame, text='Cancel', underline=0, command=cancel)
  cancel_button.grid(row=0, column=3, sticky=tk.E, padx=gui.PADX_QW)
  
  gui.bind_buttons_window(frame.winfo_toplevel(), ok_button=ok_button, cancel_button=cancel_button)
  
  for button in (ok_button, cancel_button):
    gui.enable_traversal_button(button)


def make_calibrate(frame, variables, class_names):
  RESIZABLE = True
  SIZE = (520, 500)
  
  window = frame.master
  parent = window.master
  
  gui.customize_window(window, TITLE, resizable=RESIZABLE, size=SIZE,
    location=gui.location_center_window(parent, SIZE))
  
  frame.rowconfigure(0, weight=1) # make calibration frame vertically resizable
  frame.columnconfigure(0, weight=1) # make calibration frame horizontally resizable
  
  calibration_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=4)
  calibration_frame.grid(row=0, sticky=tk.NSEW)
  
  calibration_text = gui.make_text(calibration_frame, font=('TkDefaultFont', 24))[1][0]
  gui.text_embed(calibration_text)
  
  # put in 100% as defaults if the calibration is empty/too short
  calibration_variable = variables['calibration']
  calibration_variable += [100] * (len(class_names) - len(calibration_variable))
  
  scales = []
  
  for c, class_name in enumerate(class_names):
    scale_frame = ttk.Frame(calibration_text)
    
    scale = gui.make_scale(scale_frame, name='%d. %s' % (c + 1, class_name),
      to=200)[1]
    
    scale.set(int(calibration_variable[c]))
    scales.append(scale)
    
    scale_frame.columnconfigure(0, weight=2, uniform='class_column')
    scale_frame.columnconfigure(1, weight=1, uniform='class_column')
    
    gui.insert_embed(calibration_text, scale_frame)
  
  footer_frame = ttk.Frame(frame)
  footer_frame.grid(row=1, sticky=tk.EW, pady=gui.PADY_N)
  
  def ok():
    variables['calibration'] = [int(s.get()) for s in scales]
    gui.release_modal_window(window)
  
  make_footer(
    footer_frame,
    ok,
    lambda: gui.release_modal_window(window)
  )
  
  gui.set_modal_window(window)