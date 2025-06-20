import tkinter as tk
from tkinter import ttk
import os

try:
  import tkinterdnd2.TkinterDnD as tkdnd
except ImportError:
  tkdnd = None

import yamosse.root as yamosse_root

from . import std as gui_std

WINDOWS_ICONPHOTO_BUGFIX = True

IMAGES_DIR = 'images'

get_root_window = None
get_root_images = None


# GUI
def _root_window():
  root_window = None
  
  def get():
    nonlocal root_window
    
    if not root_window:
      root_window = tkdnd.Tk() if tkdnd else tk.Tk()
    
    return root_window
  
  return get

get_root_window = _root_window()


def bind_buttons_window(window, ok_button=None, cancel_button=None):
  window.unbind(('<Return>', '<Escape>'))
  
  if ok_button:
    assert window == ok_button.winfo_toplevel(), 'ok_button window mismatch'
    ok_button['default'] = tk.ACTIVE
    window.bind('<Return>', lambda e: ok_button.invoke())
  
  if cancel_button:
    assert window == cancel_button.winfo_toplevel(), 'cancel_button window mismatch'
    cancel_button['default'] = tk.NORMAL
    window.bind('<Escape>', lambda e: cancel_button.invoke())


def release_modal_window(window):
  parent = window.master
  
  # this must be done before destroying the window
  # otherwise the window behind this one will not take focus back
  try:
    parent.attributes('-disabled', False)
  except tk.TclError: pass # not supported on this OS
  
  window.grab_release() # is not necessary on Windows, but is necessary on other OS's
  parent.focus_set()


def set_modal_window(window, delete_window=release_modal_window):
  # call the release function when the close button is clicked
  window.protocol('WM_DELETE_WINDOW', lambda: delete_window(window))
  
  # make the window behind us play the "bell" sound if we try and interact with it
  try:
    window.master.attributes('-disabled', True)
  except tk.TclError: pass # not supported on this OS
  
  # turns on WM_TRANSIENT_FOR on Linux (X11) which modal dialogs are meant to have
  # this should be done before setting the window type to dialog
  # see https://tronche.com/gui/x/icccm/sec-4.html#WM_TRANSIENT_FOR
  window.transient()
  
  # disable the minimize and maximize buttons
  # Windows
  try:
    window.attributes('-toolwindow', True)
  except tk.TclError: pass # not supported on this OS
  
  # Linux (X11)
  # see type list here: https://specifications.freedesktop.org/wm-spec/latest/ar01s05.html#id-1.6.7
  try:
    window.attributes('-type', 'dialog')
  except tk.TclError: pass # not supported on this OS
  
  # wait for window to be visible
  # (necessary on Linux, does nothing on Windows but it doesn't matter there)
  window.wait_visibility()
  
  # bring window to front, focus it, and prevent interacting with window behind us
  window.lift()
  window.focus_set()
  window.grab_set()


def location_center_window(parent, size):
  left, top = size
  
  return (
    parent.winfo_x() + (parent.winfo_width() / 2) - (left / 2),
    parent.winfo_y() + (parent.winfo_height() / 2) - (top / 2)
  )


def customize_window(window, title, resizable=True, size=None, location=None, iconphotos=None):
  window.title(title)
  window.resizable(resizable, resizable)
  
  if size:
    window.geometry('%dx%d+%d+%d' % (size + location) if location else '%dx%d' % size)
  
  if iconphotos:
    if window == get_root_window():
      # in this case make this the default icon
      # note that it is still necessary to call iconphoto before this
      # because Windows has a bug where you need to call iconphoto with default off first
      # otherwise it will use the wrong icon size
      if WINDOWS_ICONPHOTO_BUGFIX: window.iconphoto(False, *iconphotos)
      window.iconphoto(True, *iconphotos)
    else:
      window.iconphoto(False, *iconphotos)


def make_window(window, make_frame, *args, **kwargs):
  window.rowconfigure(0, weight=1) # make frame vertically resizable
  window.columnconfigure(0, weight=1) # make frame horizontally resizable
  
  style = ttk.Style(window)
  style.configure('Debug.TFrame', background='Red', relief=tk.GROOVE)
  style.configure('Title.TLabel', font=('Trebuchet', 18))
  
  frame = ttk.Frame(window)
  frame.grid(row=0, column=0, sticky=tk.NSEW, padx=gui_std.PADX_EW, pady=gui_std.PADY_NS)
  return window, make_frame(frame, *args, **kwargs)


def _root_images():
  root_images = None
  
  def get():
    nonlocal root_images
    
    get_root_window()
    
    if not root_images:
      def scandir(path, callback):
        result = {}
        
        with os.scandir(path) as scandir:
          for scandir_entry in scandir:
            item = callback(scandir_entry)
            
            if item:
              key, value = item
              result[key] = value
        
        return result
      
      def callback_image(entry, make_image):
        name = entry.name.lower()
        
        if entry.is_dir():
          return (name, scandir(entry.path, lambda image_entry: callback_image(
            image_entry, make_image)))
        
        try:
          return (name, make_image(file=entry.path))
        except tk.TclError:
          pass
        
        return None
      
      def callback_images(entry):
        if not entry.is_dir(): return None
        
        image = entry.name.title()
        
        return (image, scandir(entry.path, lambda image_entry: callback_image(
          image_entry, getattr(tk, ''.join((image, 'Image'))))))
      
      root_images = scandir(yamosse_root.root(IMAGES_DIR), callback_images)
    
    return root_images
  
  return get

get_root_images = _root_images()


def get_variables_from_object(object_):
  get_root_window()
  
  variable = None
  variables = {}
  
  for key, value in vars(object_).items():
    if isinstance(value, float):
      variable = tk.DoubleVar()
    elif isinstance(value, int):
      variable = tk.IntVar()
    elif isinstance(value, str):
      variable = tk.StringVar()
    else:
      variables[key] = value
      continue
    
    variable.set(value)
    variables[key] = variable
  
  return variables


def set_variables_to_object(variables, object_):
  VARIABLE_TYPES = (tk.DoubleVar, tk.IntVar, tk.StringVar)
  
  for key, value in variables.items():
    if isinstance(value, VARIABLE_TYPES):
      setattr(object_, key, value.get())
      continue
    
    setattr(object_, key, value)


def threaded():
  assert tk.Tcl().eval('set tcl_platform(threaded)'), 'Non-threaded builds are not supported.'


def gui(make_frame, *args, child=False, **kwargs):
  root_window = get_root_window()
  
  return make_window(
    root_window if not child else tk.Toplevel(root_window),
    make_frame,
    *args,
    **kwargs
  )