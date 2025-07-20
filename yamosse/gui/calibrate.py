import tkinter as tk
from tkinter import ttk

from .. import gui

TITLE = 'Calibrate'


def make_footer(frame, window):
  frame.columnconfigure(2, weight=1)
  
  # TODO: undoable commands
  undo_button = ttk.Button(frame, text='Undo', width=5,
    image=gui.get_root_images()['Photo']['undo.gif'], compound=tk.LEFT)
  
  undo_button.grid(row=0, column=0, sticky=tk.W)
  
  redo_button = ttk.Button(frame, text='Redo', width=5,
    image=gui.get_root_images()['Photo']['redo.gif'], compound=tk.LEFT)
  
  redo_button.grid(row=0, column=1, sticky=tk.W, padx=gui.PADX_QW)
  
  ok_button = ttk.Button(frame, text='OK', underline=0,
    command=lambda: gui.release_modal_window(window), default=tk.ACTIVE)
  
  ok_button.grid(row=0, column=3, sticky=tk.E, padx=gui.PADX_QW)
  
  cancel_button = ttk.Button(frame, text='Cancel', underline=0,
    command=lambda: gui.release_modal_window(window))
  
  cancel_button.grid(row=0, column=4, sticky=tk.E, padx=gui.PADX_QW)
  
  gui.bind_buttons_window(window, ok_button=ok_button, cancel_button=cancel_button)
  
  for button in (ok_button, cancel_button):
    gui.enable_traversal_button(button)


def make_calibrate(frame, class_names):
  RESIZABLE = True
  SIZE = (450, 500)
  
  window = frame.master
  parent = window.master
  
  gui.customize_window(window, TITLE, resizable=RESIZABLE, size=SIZE,
    location=gui.location_center_window(parent, SIZE))
  
  frame.rowconfigure(0, weight=1) # make classes frame vertically resizable
  frame.columnconfigure(0, weight=1) # make classes frame horizontally resizable
  
  classes_frame = ttk.Frame(frame, relief=tk.SUNKEN, borderwidth=4)
  classes_frame.grid(row=0, sticky=tk.NSEW)
  
  classes_text = gui.make_text(classes_frame, font=('TkDefaultFont', 24))[1][0]
  gui.embed_text(classes_text)
  
  for c in range(len(class_names)):
    scale_frame = ttk.Frame(classes_text)
    
    scale_frame.columnconfigure(0, weight=2,
      uniform='class_column') # make class columns uniform
    
    scale_frame.columnconfigure(1, weight=1,
      uniform='class_column') # make class columns uniform
    
    scale = gui.make_scale(scale_frame, name='%d. %s' % (c + 1, class_names[c]),
      to=200)[1]
    
    scale.set(100) # TODO: from options
    gui.embed_insert(classes_text, scale_frame)
  
  footer_frame = ttk.Frame(frame)
  footer_frame.grid(row=1, sticky=tk.EW, pady=gui.PADY_N)
  
  make_footer(footer_frame, window)
  
  gui.set_modal_window(window)