import tkinter as tk
from tkinter import ttk, messagebox
from os import fsencode as fsenc
from threading import Event

import yamosse.recording as yamosse_recording

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
  VOLUME_MAXIMUM = 100
  
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
  
  recording_button = ttk.Button(
    row_frame,
    text='Start Recording',
    image=record_image,
    compound=tk.LEFT
  )
  
  recording_button.grid(row=0, column=0, sticky=tk.W)
  
  volume_variable = tk.IntVar()
  volume_after = None
  
  volume_frame = ttk.Frame(row_frame)
  volume_frame.grid(row=0, column=1, sticky=tk.EW, padx=gui.PADX_HW)
  
  gui_progressbar.make_progressbar(
    volume_frame,
    variable=volume_variable,
    maximum=VOLUME_MAXIMUM,
    task=False
  )
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_QN)
  
  input_devices, input_default = yamosse_recording.input_devices()
  input_device_variable = variables['input_device']
  
  if str(input_device_variable.get()) not in input_devices:
    input_device_variable.set(input_default)
  
  gui.make_combobox(row_frame, name='Device:', textvariable=input_device_variable,
    values=list(input_devices.keys()), width=72, state=('readonly',))
  
  def show_volume():
    nonlocal volume_after
    
    volume_variable.set(int(recording.volume * VOLUME_MAXIMUM))
    volume_after = volume_frame.after(yamosse_recording.MILLISECONDS, show_volume)
  
  def toggle_recording():
    nonlocal stop
    nonlocal recording
    
    if not recording:
      recording_button.configure(text='Stop Recording', image=stop_image)
      stop.clear()
      recording = record(stop=stop, device=input_devices[str(input_device_variable.get())])
      show_volume()
    else:
      volume_frame.after_cancel(volume_after)
      stop.set()
      recording = None
      recording_button.configure(text='Start Recording', image=record_image)
  
  recording_button['command'] = toggle_recording
  
  window.bind('<Control-c>', lambda e: toggle_recording())
  window.protocol('WM_DELETE_WINDOW', lambda: ask_save(window, stop, recording))