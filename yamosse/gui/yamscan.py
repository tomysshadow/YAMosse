import tkinter as tk
from tkinter import ttk, messagebox

from . import gui
from . import progress as gui_progress

ASK_CANCEL_MESSAGE = 'Are you sure you want to cancel the YAMScan?'


# YAMScan Widgets
def ask_cancel(window, title, footer_yamscan_widgets):
  open_output_file_button, done_button = footer_yamscan_widgets
  
  # while this may feel like a bit of a hack, doing it this way ensures that
  # there is no possible desync between what the button says and whether the message box appears
  if str(done_button['text']) == 'OK':
    return True
  
  return messagebox.askyesno(
    parent=window, title=title, message=ASK_CANCEL_MESSAGE, default=messagebox.NO)


def make_footer(frame, log_text, open_output_file, done):
  COPIED_TO_CLIPBOARD_DELAY_MS = 3000
  
  frame.columnconfigure(1, weight=1) # make copied to clipboard label horizontally resizable
  
  copied_to_clipboard_label = ttk.Label(frame, text='Copied to clipboard.')
  copied_to_clipboard_after = None
  
  def copy_to_clipboard():
    nonlocal copied_to_clipboard_after
    
    copied_to_clipboard_label.clipboard_clear()
    copied_to_clipboard_label.clipboard_append(log_text.get('1.0', tk.END))
    copied_to_clipboard_label.grid(row=0, column=1, sticky=tk.W, padx=gui.PADX_QW)
    
    if copied_to_clipboard_after:
      copied_to_clipboard_label.after_cancel(copied_to_clipboard_after)
    
    def copied_to_clipboard():
      copied_to_clipboard_label.grid_remove()
      copied_to_clipboard_after = None
    
    copied_to_clipboard_after = copied_to_clipboard_label.after(
      COPIED_TO_CLIPBOARD_DELAY_MS,
      copied_to_clipboard
    )
  
  # this button does not have an accelerator because the user can copy the text
  # by using the Ctrl + A, Ctrl + C keycombo
  copy_to_clipboard_button = ttk.Button(frame, text='Copy to Clipboard',
    image=gui.get_root_images()['Photo']['copy.gif'], compound=tk.LEFT,
    command=copy_to_clipboard)
  
  copy_to_clipboard_button.grid(row=0, column=0, sticky=tk.W)
  gui.widen_button(copy_to_clipboard_button)
  
  open_output_file_button = ttk.Button(frame, text='Open Output File', underline=1,
    command=open_output_file)
  
  open_output_file_button.grid(row=0, column=2, sticky=tk.E, padx=gui.PADX_QW)
  gui.enable_widget(open_output_file_button, enabled=False)
  
  done_button = ttk.Button(frame, text='Cancel', underline=0,
    command=done, default=tk.ACTIVE)
  
  done_button.grid(row=0, column=3, sticky=tk.E, padx=gui.PADX_QW)
  gui.bind_buttons_window(done_button.winfo_toplevel(), cancel_button=done_button)
  
  for button in (open_output_file_button, done_button):
    gui.enable_traversal_button(button)
  
  return open_output_file_button, done_button


def show_yamscan(widgets, values=None):
  DONE_VALUES = ('OK', 'Cancel')
  
  window, progressbar_widgets, progressbar_variable, log_text, footer_yamscan_widgets = widgets
  
  def callback():
    if not window.children: return
    if not values: return
    
    if 'progressbar' in values:
      gui.configure_progressbar(
        progressbar_widgets, progressbar_variable, values['progressbar'])
    
    if 'log' in values:
      log_text['state'] = tk.NORMAL
      
      try:
        gui.delete_lines_text(log_text)
        log_text.insert(tk.END, '%s\n' % values['log'])
        log_text.see(tk.END)
      finally:
        log_text['state'] = tk.DISABLED
    
    if 'done' in values:
      done_value = values['done']
      assert done_value in DONE_VALUES, 'done_value must be in %r' % (DONE_VALUES,)
      
      open_output_file_button, done_button = footer_yamscan_widgets
      
      ok = done_value == 'OK'
      gui.enable_widget(open_output_file_button, enabled=ok)
      
      gui.disable_traversal_button(done_button)
      done_button['text'] = done_value
      gui.enable_traversal_button(done_button)
      
      gui.bind_buttons_window(
        window,
        ok_button=done_button if ok else None,
        cancel_button=done_button if not ok else None
      )
  
  try:
    # for thread safety
    # it's not safe to have a non-GUI thread interact directly with widgets
    # so we queue this for when idle
    window.after_idle(callback)
  except:
    if window.children: raise
    return False
  
  return window.children


def make_yamscan(frame, title, open_output_file, progressbar_maximum=100):
  RESIZABLE = True
  SIZE = (480, 360)
  
  gui.threaded()
  
  window = frame.master
  parent = window.master
  
  gui.customize_window(window, title, resizable=RESIZABLE, size=SIZE,
    location=gui.location_center_window(parent, SIZE))
  
  frame.rowconfigure(1, weight=1) # make log frame vertically resizable
  frame.columnconfigure(0, weight=1) # one column layout
  
  # because this window is a dialog, it won't actually be present in the taskbar
  # we instead want the taskbar progress to be shown in the parent window
  progressbar_frame = ttk.Frame(frame)
  progressbar_frame.grid(row=0, sticky=tk.EW)
  progressbar_variable = tk.IntVar()
  progressbar_widgets = gui.make_progressbar(progressbar_frame, progressbar_variable,
    maximum=progressbar_maximum, state=gui_progress.LOADING, parent=parent, task=True)[1]
  
  log_labelframe = ttk.Labelframe(frame, text='Log', padding=gui.PADDING_HNSEW)
  log_labelframe.grid(row=1, sticky=tk.NSEW, pady=gui.PADY_N)
  log_text = gui.make_text(log_labelframe, takefocus=True)[1][0]
  #gui.prevent_default_widget(log_text)
  gui.enable_widget(log_text, enabled=False)
  
  def select_all_log_text(e):
    # in theory you'd think setting the focus would be enough on its own
    # but it seems to occur after the actual text selection would
    log_text.focus_set()
    log_text.tag_add(tk.SEL, '1.0', tk.END)
  
  # auto focus the log text when user hits Ctrl + A so they can select and copy the contents
  log_text.winfo_toplevel().bind('<Control-a>', select_all_log_text)
  
  footer_yamscan_widgets = None
  
  def done(window):
    if not ask_cancel(window, title, footer_yamscan_widgets): return
    
    gui.configure_progressbar(
      progressbar_widgets, progressbar_variable, gui_progress.RESET)
    
    gui.release_modal_window(window)
  
  footer_yamscan_frame = ttk.Frame(frame)
  footer_yamscan_frame.grid(row=2, sticky=tk.EW, pady=gui.PADY_N)
  
  footer_yamscan_widgets = make_footer(
    footer_yamscan_frame,
    log_text,
    open_output_file,
    lambda: done(window)
  )
  
  gui.set_modal_window(window, done)
  return window, progressbar_widgets, progressbar_variable, log_text, footer_yamscan_widgets