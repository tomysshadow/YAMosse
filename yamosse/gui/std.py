import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shlex
import os

try:
  import tkinterdnd2
except ImportError:
  tkinterdnd2 = None

from . import progress as gui_progress

PADDING = 12
PADDING_NSEW = PADDING
PADDING_NS = (0, PADDING)
PADDING_EW = (PADDING, 0)
PADDING_N = (0, PADDING, 0, 0)
PADDING_S = (0, 0, 0, PADDING)
PADDING_E = (0, 0, PADDING, 0)
PADDING_W = (PADDING, 0, 0, 0)

PADDING_H = PADDING // 2
PADDING_HNSEW = PADDING_H
PADDING_HNS = (0, PADDING_H)
PADDING_HEW = (PADDING_H, 0)
PADDING_HN = (0, PADDING_H, 0, 0)
PADDING_HS = (0, 0, 0, PADDING_H)
PADDING_HE = (0, 0, PADDING_H, 0)
PADDING_HW = (PADDING_H, 0, 0, 0)

PADDING_Q = PADDING // 4
PADDING_QNSEW = PADDING_Q
PADDING_QNS = (0, PADDING_Q)
PADDING_QEW = (PADDING_Q, 0)
PADDING_QN = (0, PADDING_Q, 0, 0)
PADDING_QS = (0, 0, 0, PADDING_Q)
PADDING_QE = (0, 0, PADDING_Q, 0)
PADDING_QW = (PADDING_Q, 0, 0, 0)

PADX_EW = PADDING
PADX_E = (0, PADDING)
PADX_W = (PADDING, 0)

PADX_HEW = PADDING_H
PADX_HE = (0, PADDING_H)
PADX_HW = (PADDING_H, 0)

PADX_QEW = PADDING_Q
PADX_QE = (0, PADDING_Q)
PADX_QW = (PADDING_Q, 0)

PADY_NS = PADDING
PADY_N = (PADDING, 0)
PADY_S = (0, PADDING)

PADY_HNS = PADDING_H
PADY_HN = (PADDING_H, 0)
PADY_HS = (0, PADDING_H)

PADY_QNS = PADDING_Q
PADY_QN = (PADDING_Q, 0)
PADY_QS = (0, PADDING_Q)

UNIT_CLASSES = 'classes'
UNIT_SECONDS = 'seconds'

BUTTONS_COLUMN_LEFT = 0
BUTTONS_COLUMN_CENTER = 50
BUTTONS_COLUMN_RIGHT = 100


# Standard Widgets
def enable_widget(widget, enabled=True):
  widget_class = widget.winfo_class()
  
  if widget_class in ('Frame', 'Labelframe', 'TFrame', 'TLabelframe'):
    for child_widget in widget.winfo_children():
      enable_widget(child_widget, enabled)
    
    return
  
  if widget_class in ('Text', 'Entry', 'TEntry'):
    widget['cursor'] = 'ibeam' if enabled else ''
  
  widget['state'] = tk.NORMAL if enabled else tk.DISABLED


def prevent_default_widget(widget):
  widget.bindtags((str(widget),))


def make_widgets(frame, make_widget, names,
  orient=tk.HORIZONTAL, cell=0, sticky=tk.W, padding=PADDING, **kwargs):
  ORIENTS = (tk.HORIZONTAL, tk.VERTICAL)
  
  assert orient in ORIENTS, 'orient must be in %r' % (ORIENTS,)
  
  widgets = []
  if not names: return widgets
  
  last = len(names) - 1
  
  x = 'row'
  y = 'column'
  pad = 'padx'
  
  if orient == tk.VERTICAL:
    x = 'column'
    y = 'row'
    pad = 'pady'
  
  # float divide is used here in case padding is not even
  padding = padding / 2 if last != 0 else 0
  
  # first widget
  widget = make_widget(frame, text=names[0], **kwargs)
  widget.grid({x: cell, y: 0, pad: (0, padding)}, sticky=sticky)
  widgets.append(widget)
  
  # exit if the first widget is the last widget
  if last == 0: return widgets
  
  # middle widgets
  for middle in range(last - 1):
    widget = make_widget(frame, text=names[middle], **kwargs)
    widget.grid({x: cell, y: middle, pad: padding}, sticky=sticky)
    widgets.append(widget)
  
  # last widget
  widget = make_widget(frame, text=names[last], **kwargs)
  widget.grid({x: cell, y: last, pad: (padding, 0)}, sticky=sticky)
  widgets.append(widget)
  return widgets


def _accelerator_sequence_button(button, underline):
  assert underline >= 0, 'underline must be greater than or equal to zero'
  return '<Alt-%c>' % str(button['text'])[underline].lower()


def accelerate_button(button):
  underline = int(button['underline'])
  
  if underline < 0:
    return
  
  button.winfo_toplevel().bind(
    _accelerator_sequence_button(button, underline),
    lambda e: button.focus_set()
  )


def decelerate_button(button):
  underline = int(button['underline'])
  
  if underline < 0:
    return
  
  button.winfo_toplevel().unbind(_accelerator_sequence_button(button, underline))


def link_radiobuttons(radiobuttons, variable):
  radiobuttons = dict(radiobuttons)
  
  widgets = tuple(radiobuttons.values())
  radiobuttons = tuple(radiobuttons.keys())
  
  def show():
    for w in range(len(widgets)):
      widget = widgets[w]
      
      if widget:
        enabled = (w == variable.get())
        enable_widget(widget, enabled=enabled)
  
  for r in range(len(radiobuttons)):
    radiobuttons[r].configure(value=r, variable=variable, command=show)
  
  show()


def make_labelframe(frame, sticky=tk.NSEW, padding=PADDING_HNSEW, **kwargs):
  frame.rowconfigure(0, weight=1) # make labelframe vertically resizable
  frame.columnconfigure(0, weight=1) # make labelframe horizontally resizable
  
  labelframe = ttk.Labelframe(frame, padding=padding, **kwargs)
  labelframe.grid(sticky=sticky)
  return labelframe


def make_name(frame, name):
  if not name: return None
  
  label = ttk.Label(frame, text=name)
  label.grid(row=0, column=0, sticky=tk.W)
  return label


def make_scrollbar(widget, xscroll=False, yscroll=True):
  master = widget.master
  
  xscrollbar = None
  yscrollbar = None
  
  if xscroll:
    xscrollbar = ttk.Scrollbar(master, command=widget.xview, orient=tk.HORIZONTAL)
    xscrollbar.grid(row=1, column=0, sticky=tk.EW)
    
    widget['xscrollcommand'] = xscrollbar.set
  
  if yscroll:
    yscrollbar = ttk.Scrollbar(master, command=widget.yview, orient=tk.VERTICAL)
    yscrollbar.grid(row=0, column=1, sticky=tk.NS)
    
    widget['yscrollcommand'] = yscrollbar.set
  
  return xscrollbar, yscrollbar


def make_unit(frame, unit):
  if not unit: return None
  
  unit = ' %s' % unit
  label = ttk.Label(frame, text=unit)
  label.grid(row=0, column=2, sticky=tk.E)
  return label


def make_percent(frame):
  WIDTH = 5
  
  label = ttk.Label(frame, width=WIDTH, anchor=tk.CENTER)
  label.grid(row=0, column=2, sticky=tk.E)
  return label


def make_entry(frame, textvariable, name='', **kwargs):
  frame.rowconfigure(0, weight=1) # make entry vertically centered
  frame.columnconfigure(1, weight=1) # make entry horizontally resizable
  
  entry = ttk.Entry(frame, textvariable=textvariable, **kwargs)
  entry.grid(row=0, column=1, sticky=tk.EW, padx=PADX_QW)
  return make_name(frame, name), entry


def make_spinbox(frame, textvariable, name='', wrap=False, unit='', **kwargs):
  frame.rowconfigure(0, weight=1) # make spinbox vertically centered
  frame.columnconfigure(1, weight=1) # make spinbox horizontally resizable
  
  spinbox = ttk.Spinbox(frame, textvariable=textvariable, wrap=wrap, **kwargs)
  spinbox.grid(row=0, column=1, sticky=tk.EW, padx=PADX_QW)
  return make_name(frame, name), spinbox, make_unit(frame, unit)


def make_combobox(frame, textvariable, name='', state=None, **kwargs):
  frame.rowconfigure(0, weight=1) # make combobox vertically centered
  frame.columnconfigure(1, weight=1) # make combobox horizontally resizable
  
  combobox = ttk.Combobox(frame, textvariable=textvariable, **kwargs)
  combobox.grid(row=0, column=1, sticky=tk.EW, padx=PADX_QW)
  
  if state:
    combobox.state(state)
  
  return make_name(frame, name), combobox


def make_scale(frame, variable, name='', **kwargs):
  frame.rowconfigure(0, weight=1) # make scale vertically centered
  frame.columnconfigure(1, weight=1) # make scale horizontally resizable
  
  percent_label = make_percent(frame)
  
  # unused text argument is just so this will work as scale command
  # note that here we use the scale command instead of a trace callback on the variable
  # because this also sets the variable, so it would be recursive otherwise
  def show(text=''):
    value = variable.get()
    variable.set(value) # increment in steps
    text = '%d%%' % value
    percent_label['text'] = text
  
  scale = ttk.Scale(frame, variable=variable,
    from_=0, to=100, orient=tk.HORIZONTAL, command=show, **kwargs)
  
  scale.grid(row=0, column=1, sticky=tk.EW, padx=PADX_QW)
  show()
  return make_name(frame, name), scale, percent_label


def delete_lines_text(text, max_lines=1000):
  lines = text.index(tk.END)
  lines = int(lines[:lines.index('.')]) - max_lines
  
  if lines > 0:
    text.delete('1.0', '%d.%s' % (lines, tk.END))


def make_text(frame, name='', width=10, height=10,
  autoseparators=False, wrap=tk.WORD, font=None, xscroll=False, yscroll=True, **kwargs):
  FONT = ('Courier', '10')
  
  frame.rowconfigure(1, weight=1) # make scrollbar frame vertically resizable
  frame.columnconfigure(0, weight=1) # make scrollbar frame horizontally resizable
  
  scrollbar_frame = ttk.Frame(frame)
  scrollbar_frame.grid(row=1, sticky=tk.NSEW)
  
  scrollbar_frame.rowconfigure(0, weight=1) # make text vertically resizable
  scrollbar_frame.columnconfigure(0, weight=1) # make text horizontally resizable
  
  text = tk.Text(scrollbar_frame, width=width, height=height,
    autoseparators=autoseparators, wrap=wrap, font=font if font else FONT, **kwargs)
  
  text.grid(row=0, column=0, sticky=tk.NSEW)
  return make_name(frame, name), (text, make_scrollbar(text, xscroll, yscroll))


def _is_even(num):
  return not num & 1


def make_listbox(frame, items, name='',
  selectmode=tk.BROWSE, xscroll=False, yscroll=True, **kwargs):
  BG = 'Azure'
  BG2 = 'Azure2'
  
  frame.rowconfigure(0, weight=1) # make scrollbar frame vertically resizable
  frame.columnconfigure(0, weight=1) # make scrollbar frame horizontally resizable
  
  scrollbar_frame = ttk.Frame(frame)
  scrollbar_frame.grid(row=0, sticky=tk.NSEW)
  
  scrollbar_frame.rowconfigure(0, weight=1) # make listbox vertically resizable
  scrollbar_frame.columnconfigure(0, weight=1) # make listbox horizontally resizable
  
  listbox = tk.Listbox(scrollbar_frame, selectmode=selectmode, bg=BG, **kwargs)
  listbox.grid(row=0, column=0, sticky=tk.NSEW)
  
  for item in range(len(items)):
    listbox.insert(tk.END, items[item])
    listbox.itemconfig(item, bg=BG if _is_even(item) else BG2)
  
  name_frame = ttk.Frame(frame)
  name_frame.grid(row=1, sticky=tk.EW, pady=PADY_QN)
  
  name_frame.columnconfigure(0, weight=1) # make name label column horizontally resizable
  
  buttons_frame = ttk.Frame(name_frame)
  buttons_frame.grid(row=0, column=1, sticky=tk.E)
  buttons = []
  
  if selectmode == tk.MULTIPLE:
    def select_all():
      listbox.selection_set(0, tk.END)
    
    def select_none():
      listbox.selection_clear(0, tk.END)
    
    def invert_selection():
      for item in range(listbox.size()):
        if listbox.selection_includes(item):
          listbox.selection_clear(item)
        else:
          listbox.selection_set(item)
    
    buttons = [
      ttk.Button(
        buttons_frame,
        text='Select All',
        command=select_all
      ),
        
      ttk.Button(
        buttons_frame,
        text='Select None',
        command=select_none
      ),
        
      ttk.Button(
        buttons_frame,
        text='Invert Selection',
        command=invert_selection
      )
    ]
    
    for b in range(len(buttons)):
      buttons[b].grid(row=0, column=BUTTONS_COLUMN_CENTER + b, padx=PADX_QW)
  
  return make_name(name_frame, name), (listbox, make_scrollbar(listbox, xscroll, yscroll)
    ), (buttons_frame, buttons)


def _is_determinate_progressbar(progressbar):
  return str(progressbar['mode']) == 'determinate'


def configure_progressbar(widgets, variable, type_):
  progressbar, taskbar = widgets
  variable_set = False
  
  if not type_ in gui_progress.types.keys():
    variable.set(int(type_))
    return True
  
  if type_ == gui_progress.LOADING:
    if _is_determinate_progressbar(progressbar):
      progressbar['mode'] = 'indeterminate'
      variable.set(0) # must be done after setting mode to take effect
      variable_set = True
      progressbar.start() # as the last step, start the animation
  else:
    if not _is_determinate_progressbar(progressbar):
      progressbar.stop() # as the first step, stop the animation
      progressbar['mode'] = 'determinate'
      variable.set(0) # must be done after setting mode to take effect
      variable_set = True
    
    if type_ == gui_progress.DONE:
      variable.set(int(progressbar['maximum']))
      
      if taskbar: taskbar.flash_done()
      return True
    
    if type_ == gui_progress.RESET:
      variable.set(0)
      
      if taskbar: taskbar.reset()
      return True
  
  if taskbar: taskbar.set_progress_type(gui_progress.types[type_])
  return variable_set


def make_progressbar(frame, variable, name='',
  state=gui_progress.NORMAL, parent=None, task=False, **kwargs):
  frame.rowconfigure(0, weight=1) # make progressbar vertically centered
  frame.columnconfigure(1, weight=1) # make progressbar horizontally resizable
  
  percent_label = make_percent(frame)
  
  progressbar = ttk.Progressbar(frame, variable=variable,
    mode='determinate', orient=tk.HORIZONTAL, **kwargs)
  
  progressbar.grid(row=0, column=1, sticky=tk.EW, padx=PADX_QW)
  
  taskbar = None
  
  if task and gui_progress.PyTaskbar:
    if not parent: parent = frame.winfo_toplevel()
    taskbar = gui_progress.PyTaskbar.Progress(hwnd=gui_progress.hwnd(parent))
  
  value = 0
  
  def show(name='', index='', mode=''):
    nonlocal value
    
    # only update the percent label in determinate mode
    if _is_determinate_progressbar(progressbar):
      value = variable.get()
      
      if taskbar:
        taskbar.set_progress(value, int(progressbar['maximum']))
    
    text = '%d%%' % value
    percent_label['text'] = text
  
  variable.trace('w', show)
  
  widgets = (progressbar, taskbar)
  if not configure_progressbar(widgets, variable, state): show()
  return make_name(frame, name), widgets, percent_label


def make_filedialog(frame, textvariable, name='',
  asks=None, parent=None, filetypes=None, **kwargs):
  ASKS_ALL = ('openfilename', 'openfilenames', 'savefilename', 'directory')
  ASKS_FILES = ('openfilename', 'openfilenames', 'savefilename')
  
  frame.rowconfigure(0, weight=1) # make entry vertically centered
  frame.columnconfigure(0, weight=1) # make entry horizontally resizable
  
  entry = ttk.Entry(frame, textvariable=textvariable, **kwargs)
  entry.grid(row=0, sticky=tk.EW)
  
  name_frame = ttk.Frame(frame)
  name_frame.grid(row=1, sticky=tk.EW, pady=PADY_QN)
  
  name_frame.columnconfigure(0, weight=1) # make name label column horizontally resizable
  
  buttons_frame = ttk.Frame(name_frame)
  buttons_frame.grid(row=0, column=1, sticky=tk.E)
  
  def set(data):
    if not data:
      return
    
    if isinstance(data, str):
      data = (data,)
    
    textvariable.set(shlex.join(data))
  
  def show(ask='openfilename'):
    filedialog_ask = getattr(filedialog, ''.join(('ask', ask)))
    
    set(filedialog_ask(parent=parent, filetypes=filetypes
      ) if filetypes and ask != 'directory' else filedialog_ask(parent=parent))
  
  if asks == None:
    asks = ('openfilename',)
  
  buttons = []
  
  for a in range(len(asks)):
    ask = asks[a]
    
    assert ask in ASKS_ALL, 'ask must be in %r' % (ASKS_ALL,)
    
    text = 'Browse...'
    
    if ask == 'openfilenames':
      text = 'Browse Files...'
    elif ask == 'directory':
      text = 'Browse Folder...'
    
    button = ttk.Button(
      buttons_frame,
      text=text,
      command=lambda ask=ask: show(ask)
    )
    
    button.grid(row=0, column=BUTTONS_COLUMN_CENTER + a, padx=PADX_QW)
    buttons.append(button)
  
  # drag and drop
  if tkinterdnd2:
    def drop_enter(e):
      data = e.widget.tk.splitlist(e.data)
      
      if not data:
        return tkinterdnd2.REFUSE_DROP
      
      if isinstance(data, str):
        data = (str(data),)
      
      multiple = len(data) > 1
      
      # if multiple selection is not enabled, refuse multiple files
      if multiple and not 'openfilenames' in asks:
        return tkinterdnd2.REFUSE_DROP
      
      asks_no_files = not any(ask in asks for ask in ASKS_FILES)
      asks_no_dirs = multiple or not 'directory' in asks
      
      for d in data:
        if asks_no_files and os.path.isfile(d):
          return tkinterdnd2.REFUSE_DROP
        
        if asks_no_dirs and os.path.isdir(d):
          return tkinterdnd2.REFUSE_DROP
      
      return e.action
    
    def drop(e):
      set(e.widget.tk.splitlist(e.data))
      return e.action
    
    frame.drop_target_register(tkinterdnd2.DND_FILES)
    frame.dnd_bind('<<DropEnter>>', drop_enter)
    frame.dnd_bind('<<Drop>>', drop)
  
  return make_name(name_frame, name), entry, (buttons_frame, buttons)