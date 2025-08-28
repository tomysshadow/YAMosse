import tkinter as tk
from tkinter import ttk, messagebox
from threading import Lock, Event
from os import fsencode as fsenc

try:
  import yamosse.recording as yamosse_recording
except ImportError:
  yamosse_recording = None

from .. import gui
from . import progressbar as gui_progressbar

TITLE = 'Record'
RESIZABLE = False

ASK_SAVE_MESSAGE = 'Do you want to save the recording?'

VOLUME_MAXIMUM = 100


def make_record(frame, variables, record):
  window = frame.master
  window.withdraw()
  gui.customize_window(window, TITLE, resizable=RESIZABLE)
  
  if not yamosse_recording: return None
  
  frame.columnconfigure(0, weight=1) # one column layout
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=0, sticky=tk.NSEW)
  
  row_frame.columnconfigure(1, weight=1) # make progressbar frame horizontally resizable
  
  photo_images = gui.get_root_images()[gui.FSENC_PHOTO]
  record_image = photo_images[fsenc('record.gif')]
  stop_image = photo_images[fsenc('stop.gif')]
  
  start = Lock()
  stop = Event()
  recording = None
  
  recording_button = ttk.Button(
    row_frame,
    text='Start Recording',
    image=record_image,
    compound=tk.LEFT
  )
  
  recording_button.grid(row=0, column=0, sticky=tk.W)
  
  volume_after = None
  volume_after_ms = int(yamosse_recording.BLOCKSIZE_SECONDS * 1000)
  
  volume_frame = ttk.Frame(row_frame)
  volume_frame.grid(row=0, column=1, sticky=tk.EW, padx=gui.PADX_HW)
  volume_variable = tk.IntVar()
  
  gui_progressbar.Progressbar(
    volume_frame,
    variable=volume_variable,
    maximum=VOLUME_MAXIMUM,
    task=False
  )
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_HN)
  
  input_devices, input_default_name = yamosse_recording.Recording.input_devices()
  input_device_variable = variables['input_device']
  
  # set to the default if the device is not in the list
  # (maybe changed from last time, maybe we were on the default and the default changed)
  if str(input_device_variable.get()) not in input_devices:
    input_device_variable.set(input_default_name)
  
  input_devices_combobox = gui.make_combobox(row_frame,
    name='Device:', textvariable=input_device_variable,
    values=list(input_devices.keys()), width=72, state='readonly')[1]
  
  def show_volume():
    gui.set_attrs_to_variables(variables, recording.options)
    
    volume_variable.set(int(recording.volume() * VOLUME_MAXIMUM))
    start_volume()
  
  def hide_volume():
    gui.set_attrs_to_variables(variables, recording.options)
    
    volume_variable.set(0)
  
  def start_volume():
    nonlocal volume_after
    
    volume_after = volume_frame.after(volume_after_ms, show_volume)
  
  def stop_volume():
    nonlocal volume_after
    
    volume_frame.after_cancel(volume_after)
    hide_volume()
  
  def start_recording():
    nonlocal recording
    
    if recording: return
    
    recording_button.configure(text='Stop Recording', image=stop_image, command=stop_recording)
    input_devices_combobox['state'] = 'disabled'
    
    stop.clear()
    
    with start:
      recording = record(start=start, stop=stop)
      gui.set_attrs_to_variables(variables, recording.options)
    
    start_volume()
  
  def stop_recording():
    nonlocal recording
    
    if not recording: return
    
    stop_volume()
    
    stop.set()
    
    with start:
      gui.copy_attrs_to_variables(variables, recording.options)
      recording = None
    
    input_devices_combobox['state'] = 'readonly'
    recording_button.configure(text='Start Recording', image=record_image, command=start_recording)
  
  recording_button['command'] = start_recording
  window.bind('<Control-c>', lambda e: recording_button.invoke())
  
  window_bindtag = gui.bindtag_window(window)
  
  for sequence in ('<Unmap>', '<Destroy>'):
    window.bind_class(window_bindtag,
      sequence, lambda e: stop_recording(), add=True)
  
  window.protocol('WM_SAVE_YOURSELF', stop_recording)
  
  def ask_save(close):
    if recording:
      save = messagebox.askyesnocancel(
        parent=window, title=TITLE, message=ASK_SAVE_MESSAGE, default=messagebox.YES)
      
      if save is None:
        return
      
      recording.save = save
    
    close()
  
  window.protocol('WM_DELETE_WINDOW', lambda: ask_save(window.withdraw))
  return ask_save