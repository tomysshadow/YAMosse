import tkinter as tk
from tkinter import ttk, messagebox
from os import fsencode as fsenc

import yamosse.progress as yamosse_progress

from .. import gui
from . import progressbar as gui_progressbar

TITLE = 'YAMScan'
RESIZABLE = True
SIZE = (540, 430)

ASK_CANCEL_MESSAGE = 'Are you sure you want to cancel the YAMScan?'

LOG_LINES = 1000
DONE_VALUES = ('OK', 'Cancel')


def ask_cancel(window, footer_widgets):
  open_output_file_button, done_button = footer_widgets
  
  assert open_output_file_button # silence unused variable warning
  
  # while this may feel like a bit of a hack, doing it this way ensures that
  # there is no possible desync between what the button says and whether the message box appears
  if str(done_button['text']) == 'OK':
    return True
  
  return messagebox.askyesno(
    parent=window, title=TITLE, message=ASK_CANCEL_MESSAGE, default=messagebox.NO)


def make_footer(frame, log_text, open_output_file, done):
  COPIED_TO_CLIPBOARD_DELAY_MS = 3000
  
  frame.columnconfigure(1, weight=1) # make copied to clipboard label horizontally resizable
  
  copied_to_clipboard_label = ttk.Label(frame, text='Copied to clipboard.')
  copied_to_clipboard_after = None
  
  def copied_to_clipboard():
    nonlocal copied_to_clipboard_after
    
    copied_to_clipboard_label.grid_remove()
    copied_to_clipboard_after = None
  
  def copy_to_clipboard():
    nonlocal copied_to_clipboard_after
    
    copied_to_clipboard_label.clipboard_clear()
    copied_to_clipboard_label.clipboard_append(log_text.get('1.0', tk.END))
    copied_to_clipboard_label.grid(row=0, column=1, sticky=tk.W, padx=gui.PADX_QW)
    
    if copied_to_clipboard_after:
      copied_to_clipboard_label.after_cancel(copied_to_clipboard_after)
    
    copied_to_clipboard_after = copied_to_clipboard_label.after(
      COPIED_TO_CLIPBOARD_DELAY_MS,
      copied_to_clipboard
    )
  
  # this button does not have an accelerator because the user can copy the text
  # by using the Ctrl + A, Ctrl + C keycombo
  copy_to_clipboard_button = ttk.Button(frame, text='Copy to Clipboard',
    image=gui.get_root_images()[gui.ImageType.PHOTO][fsenc('copy.gif')], compound=tk.LEFT,
    command=copy_to_clipboard)
  
  copy_to_clipboard_button.grid(row=0, column=0, sticky=tk.W)
  
  open_output_file_button = ttk.Button(frame, text='Open Output File', underline=1,
    command=open_output_file, state=tk.DISABLED)
  
  open_output_file_button.grid(row=0, column=2, sticky=tk.E, padx=gui.PADX_QW)
  
  done_button = ttk.Button(frame, text='Cancel', underline=0,
    command=done, default=tk.ACTIVE)
  
  done_button.grid(row=0, column=3, sticky=tk.E, padx=gui.PADX_QW)
  gui.bind_buttons_window(done_button.winfo_toplevel(), cancel_button=done_button)
  
  for button in (open_output_file_button, done_button):
    gui.enable_traversal_button(button)
  
  return open_output_file_button, done_button


def show_yamscan(widgets, values=None):
  window, progressbar, log_text, footer_widgets = widgets
  open_output_file_button, done_button = footer_widgets
  
  def callback():
    if not window.children: return
    if not values: return
    
    value = values.get('progressbar')
    
    if value is not None:
      for function, arguments in value.items():
        args = arguments.get('args', ())
        kwargs = arguments.get('kwargs', {})
        getattr(progressbar, function)(*args, **kwargs)
    
    value = values.get('log')
    
    if value is not None:
      with gui.normal_widget(log_text):
        log_text.insert(tk.END, value)
        log_text.insert(tk.END, '\n')
        log_text.delete('1.0', '%s - %d lines' % (tk.END, LOG_LINES))
        log_text.see(tk.END)
    
    value = values.get('open_output_file')
    
    if value is not None:
      open_output_file_button['state'] = tk.NORMAL if value else tk.DISABLED
    
    value = values.get('done')
    
    if value is not None:
      if value not in DONE_VALUES:
        raise ValueError('value must be in %r' % (DONE_VALUES,))
      
      gui.disable_traversal_button(done_button)
      
      try:
        done_button['text'] = value
      finally:
        gui.enable_traversal_button(done_button)
      
      ok = value == 'OK'
      
      gui.bind_buttons_window(
        window,
        ok_button=done_button if ok else None,
        cancel_button=done_button if not ok else None
      )
      
      if ok: window.bell()
  
  return gui.after_window(window, callback)


def make_yamscan(frame, open_output_file, exit_, progressbar_maximum=100):
  window = frame.master
  parent = window.master
  
  gui.customize_window(window, title=TITLE, resizable=RESIZABLE, size=SIZE,
    location=gui.location_center_window(parent, SIZE))
  
  gui.minsize_window(window)
  
  frame.rowconfigure(1, weight=1) # make log frame vertically resizable
  frame.columnconfigure(0, weight=1) # one column layout
  
  # because this window is a dialog, it won't actually be present in the taskbar
  # we instead want the taskbar progress to be shown in the parent window
  progressbar_frame = ttk.Frame(frame)
  progressbar_frame.grid(row=0, sticky=tk.EW)
  
  progressbar = gui_progressbar.Progressbar(
    progressbar_frame,
    maximum=progressbar_maximum,
    mode=yamosse_progress.Mode.INDETERMINATE,
    parent=parent,
    task=True,
    style='Fill.TProgressbar'
  )
  
  log_labelframe = ttk.Labelframe(frame, text='Log', padding=gui.PADDING_HNSEW)
  log_labelframe.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_N)
  log_text = gui.make_text(log_labelframe,
    takefocus=True, cursor='', state=tk.DISABLED).middle[0]
  
  #log_text.bindtags(gui.default_bindtags_widget(log_text, class_=False))
  
  def select_all_log_text(e):
    # in theory you'd think setting the focus would be enough on its own
    # but it seems to occur after the actual text selection would
    log_text.focus_set()
    log_text.tag_add(tk.SEL, '1.0', tk.END)
  
  # auto focus the log text when user hits Ctrl + A so they can select and copy the contents
  window.bind('<Control-a>', select_all_log_text)
  
  footer_frame = ttk.Frame(frame)
  footer_frame.grid(row=2, sticky=tk.EW, pady=gui.PADY_N)
  
  footer_widgets = None
  
  def done(window):
    if not ask_cancel(window, footer_widgets):
      return
    
    gui.release_modal_window(window)
  
  footer_widgets = make_footer(
    footer_frame,
    log_text,
    open_output_file,
    lambda: done(window)
  )
  
  window.bind_class(gui.bindtag_window(window),
    '<Destroy>', lambda e: exit_.set(), add=True)
  
  gui.set_modal_window(window, delete_window=done)
  return window, progressbar, log_text, footer_widgets