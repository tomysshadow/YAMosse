import tkinter as tk
from tkinter import ttk, messagebox
from os import fsencode as fsenc
from threading import Event

from .. import gui
from . import progressbar as gui_progressbar

TITLE = 'Record'
RESIZABLE = False

ASK_SAVE_MESSAGE = 'Do you want to save the recording?'


def ask_save(window, stop, recording):
  if recording:
    save = messagebox.askyesnocancel(
      parent=window, title=TITLE, message=ASK_SAVE_MESSAGE, default=messagebox.YES)
    
    if save is None: return
    recording.save = save
  
  stop.set()
  window.destroy()


def make_record(frame, variables, record):
  window = frame.master
  gui.customize_window(window, TITLE, resizable=RESIZABLE)
  
  frame.columnconfigure(0, weight=1) # one column layout
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=0, sticky=tk.NSEW)
  
  row_frame.columnconfigure(1, weight=1) # make progressbar frame horizontally resizable
  
  photo_images = gui.get_root_images()[gui.FSENC_PHOTO]
  record_image = photo_images[fsenc('record.gif')]
  stop_image = photo_images[fsenc('stop.gif')]
  
  stop = Event()
  recording = None
  recording_button = None
  
  def toggle_recording():
    nonlocal stop
    nonlocal recording
    
    if not recording:
      recording_button.configure(text='Stop Recording', image=stop_image)
      stop.clear()
      recording = record(stop)
    else:
      stop.set()
      recording = None
      recording_button.configure(text='Start Recording', image=record_image)
  
  recording_button = ttk.Button(
    row_frame,
    text='Start Recording',
    image=record_image,
    compound=tk.LEFT,
    command=toggle_recording
  )
  
  recording_button.grid(row=0, column=0, sticky=tk.W)
  
  window.bind('<Control-c>', lambda e: toggle_recording())
  
  progressbar_frame = ttk.Frame(row_frame)
  progressbar_frame.grid(row=0, column=1, sticky=tk.EW, padx=gui.PADX_HW)
  
  gui_progressbar.make_progressbar(progressbar_frame, task=False)
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_QN)
  
  gui.make_combobox(row_frame, name='Device:',
    values=('A', 'B', 'C'), state=('readonly',)) # TODO
  
  window.protocol('WM_DELETE_WINDOW', lambda: ask_save(window, stop, recording))