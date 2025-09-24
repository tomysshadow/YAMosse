import tkinter as tk
from tkinter import ttk, messagebox
from threading import Lock, Event
from contextlib import ExitStack
from os import fsencode as fsenc

try:
  import yamosse.recording as yamosse_recording
except ImportError:
  yamosse_recording = None

from .. import gui
from . import progressbar as gui_progressbar

TITLE = 'Recorder'
RESIZABLE = (True, False)

ASK_SAVE_MESSAGE = 'Do you want to save the recording?'

VOLUME_MAXIMUM = 100


class Recorder:
  def __init__(self, frame, variables, record):
    window = frame.master
    window.withdraw()
    gui.customize_window(window, TITLE, resizable=RESIZABLE)
    gui.minsize_window(window)
    
    if not yamosse_recording: return
    
    frame.columnconfigure(0, weight=1) # one column layout
    
    row_frame = ttk.Frame(frame)
    row_frame.grid(row=0, sticky=tk.NSEW)
    
    row_frame.columnconfigure(1, weight=1) # make progressbar frame horizontally resizable
    
    photo_images = gui.get_root_images()[gui.ImageType.PHOTO]
    record_image = photo_images[fsenc('record.gif')]
    stop_image = photo_images[fsenc('stop.gif')]
    
    recording_button = ttk.Button(
      row_frame,
      text='Start Recording',
      image=record_image,
      compound=tk.LEFT,
      command=self._start_recording
    )
    
    recording_button.grid(row=0, column=0, sticky=tk.W)
    
    window.bind('<Control-c>', lambda e: recording_button.invoke())
    
    volume_frame = ttk.Frame(row_frame)
    volume_frame.grid(row=0, column=1, sticky=tk.EW, padx=gui.PADX_HW)
    volume_variable = tk.IntVar()
    
    gui_progressbar.Progressbar(
      volume_frame,
      name=yamosse_recording.Recording.VOLUME_NAME,
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
      values=list(input_devices), width=72, state='readonly').middle
    
    window_bindtag = gui.bindtag_window(window)
    
    for destroy, sequence in enumerate(('<Unmap>', '<Destroy>')):
      window.bind_class(
        window_bindtag,
        sequence,
        lambda e, destroy=destroy: self._stop_recording(destroy),
        add=True
      )
    
    window.protocol('WM_SAVE_YOURSELF', self._stop_recording)
    
    window.protocol(
      'WM_DELETE_WINDOW',
      lambda: self.ask_save(window.withdraw)
    )
    
    self._window = window
    self._recording_button = recording_button
    self._input_devices_combobox = input_devices_combobox
    
    self._ask = Lock()
    
    self._record_image = record_image
    self._stop_image = stop_image
    
    self._variables = variables
    self._record = record
    
    self._start = Lock()
    self._stop = Event()
    self._recording = None
    self._input_devices = input_devices
    
    self._volume_frame = volume_frame
    self._volume_variable = volume_variable
    self._volume_after = None
    self._volume_after_ms = int(yamosse_recording.Recording.BLOCKSIZE_SECONDS * 1000)
  
  def ask_save(self, close):
    with ExitStack() as exit_stack:
      exit_stack.callback(close)
      
      if not yamosse_recording:
        return
      
      recording = self._recording
      
      if not recording:
        return
      
      ask = self._ask
      
      # if the dialog is already open, focus the existing one
      if not ask.acquire(blocking=False):
        self._window.focus_force()
        exit_stack.pop_all()
        return
      
      # this try-finally can't be incorporated into the exit stack
      # the release here needs to always happen
      try:
        save = messagebox.askyesnocancel(parent=self._window,
          title=TITLE, message=ASK_SAVE_MESSAGE, default=messagebox.YES)
        
        if save is None:
          exit_stack.pop_all()
          return
        
        recording.save = save
      finally:
        ask.release()
  
  def _start_recording(self):
    recording = self._recording
    
    if recording: return
    
    # don't start recording if there are no input devices
    if str(self._variables['input_device'].get()) not in self._input_devices:
      messagebox.showwarning(parent=self._window, title=TITLE,
        message=yamosse_recording.Recording.NO_INPUT_DEVICES_MESSAGE)
      
      return
    
    self._recording_button.configure(
      text='Stop Recording',
      image=self._stop_image,
      command=self._stop_recording
    )
    
    self._input_devices_combobox['state'] = 'disabled'
    
    start = self._start
    stop = self._stop
    
    stop.clear()
    
    with start:
      recording = self._record(start=start, stop=stop)
      gui.set_attrs_to_variables(self._variables, recording.options)
    
    self._recording = recording
    self._start_volume()
  
  def _stop_recording(self, destroy=False):
    recording = self._recording
    
    if not recording: return
    
    self._stop_volume()
    self._stop.set()
    
    with self._start:
      gui.copy_attrs_to_variables(self._variables, recording.options)
      recording = None
    
    self._recording = recording
    
    if destroy: return
    
    self._input_devices_combobox['state'] = 'readonly'
    
    self._recording_button.configure(
      text='Start Recording',
      image=self._record_image,
      command=self._start_recording
    )
  
  def _start_volume(self):
    self._volume_after = self._volume_frame.after(self._volume_after_ms, self._show_volume)
  
  def _stop_volume(self):
    self._volume_frame.after_cancel(self._volume_after)
    self._hide_volume()
  
  def _show_volume(self):
    recording = self._recording
    
    gui.set_attrs_to_variables(self._variables, recording.options)
    
    self._volume_variable.set(int(recording.volume() * VOLUME_MAXIMUM))
    self._start_volume()
  
  def _hide_volume(self):
    recording = self._recording
    
    gui.set_attrs_to_variables(self._variables, recording.options)
    
    self._volume_variable.set(0)