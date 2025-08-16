import tkinter as tk
from tkinter import ttk, messagebox
from os import fsencode as fsenc
from threading import Event

from .. import gui
from . import progressbar as gui_progressbar

TITLE = 'Record'
RESIZABLE = False

ASK_CANCEL_MESSAGE = 'Are you sure you want to cancel the recording?'


def ask_cancel(window, recording_button):
  if str(recording_button['text']) == 'Start Recording': return True
  
  return messagebox.askyesno(
    parent=window, title=TITLE, message=ASK_CANCEL_MESSAGE, default=messagebox.NO)


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
  
  recording_button = None
  stop = Event()
  
  def recording():
    text = str(recording_button['text'])
    
    if text == 'Start Recording':
      recording_button.configure(text='Stop Recording', image=stop_image)
      record(stop)
    elif text == 'Stop Recording':
      stop.set()
      recording_button.configure(text='Start Recording', image=record_image)
  
  recording_button = ttk.Button(
    row_frame,
    text='Start Recording',
    image=record_image,
    compound=tk.LEFT,
    command=recording
  )
  
  recording_button.grid(row=0, column=0, sticky=tk.W)
  
  window.bind('<Control-c>', lambda e: recording())
  
  progressbar_frame = ttk.Frame(row_frame)
  progressbar_frame.grid(row=0, column=1, sticky=tk.EW, padx=gui.PADX_HW)
  
  gui_progressbar.make_progressbar(progressbar_frame, task=False)
  
  row_frame = ttk.Frame(frame)
  row_frame.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_QN)
  
  gui.make_combobox(row_frame, name='Device:',
    values=('A', 'B', 'C'), state=('readonly',)) # TODO
  
  def done():
    # TODO: should be Yes/No/Cancel
    if not ask_cancel(window, recording_button): return
    
    stop.set()
    window.destroy()
  
  window.protocol('WM_DELETE_WINDOW', done)