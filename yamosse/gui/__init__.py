import tkinter as tk
from tkinter import messagebox
import traceback
from threading import Lock


def _init():
  reported = False
  reported_lock = Lock()
  
  tk_report_callback_exception = tk.Tk.report_callback_exception
  
  def report_callback_exception(tk, exc, val, tb):
    tk_report_callback_exception(tk, exc, val, tb)
    
    with reported_lock:
      if reported: return
      reported = True
    
    try:
      with open('traceback.txt', 'w') as file:
        traceback.print_exception(exc, val, tb, file=file)
    except OSError: pass
    
    messagebox.showerror(title='Exception in Tkinter callback',
      message=''.join(traceback.format_exception(exc, val, tb)))
    
    raise val
  
  tk.Tk.report_callback_exception = report_callback_exception


_init()