import tkinter as tk
from tkinter import messagebox
import traceback


def _init():
  tk_report_callback_exception = tk.Tk.report_callback_exception
  
  def report_callback_exception(tk, exc, val, tb):
    tk_report_callback_exception(tk, exc, val, tb)
    
    try:
      with open('traceback.txt', 'w') as file:
        traceback.print_exception(exc, val, tb, file=file)
    except OSError: pass
    
    messagebox.showerror(title='Exception in Tkinter callback',
      message=''.join(traceback.format_exception(exc, val, tb)))
    
    raise val
  
  tk.Tk.report_callback_exception = report_callback_exception


_init()