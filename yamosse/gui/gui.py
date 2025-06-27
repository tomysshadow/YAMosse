import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import shlex
import os

try:
  import tkinterdnd2
  import tkinterdnd2.TkinterDnD as tkdnd
except ImportError:
  tkinterdnd2 = None
  tkdnd = None

import yamosse.root as yamosse_root
import yamosse.progress as yamosse_progress

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

MINSIZE_ROW_LABELS = 21
MINSIZE_ROW_RADIOBUTTONS = MINSIZE_ROW_LABELS

WINDOWS_ICONPHOTO_BUGFIX = True

IMAGES_DIR = 'images'

get_root_window = None
get_root_images = None


def enable_widget(widget, enabled=True, cursor=True):
  try:
    widget['state'] = tk.NORMAL if enabled else tk.DISABLED
    
    # we also change the cursor here, still in the same try block
    # this way, we'll only attempt to change the cursor
    # if we were successfully able to change the state
    if cursor:
      if enabled:
        try:
          widget['cursor'] = widget.normalcursor
          del widget.normalcursor
        except AttributeError: pass
      else:
        widget.normalcursor = widget['cursor']
        widget['cursor'] = ''
  except tk.TclError: pass
  
  for child_widget in widget.winfo_children():
    enable_widget(child_widget, enabled=enabled, cursor=cursor)


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


def traversal_button():
  def sequence(button, underline):
    assert underline >= 0, 'underline must be greater than or equal to zero'
    return '<Alt-%c>' % str(button['text'])[underline].lower()
  
  def enable(button):
    underline = int(button['underline'])
    
    if underline < 0:
      return
    
    button.winfo_toplevel().bind(
      sequence(button, underline),
      lambda e: button.focus_set()
    )
  
  def disable(button):
    underline = int(button['underline'])
    
    if underline < 0:
      return
    
    button.winfo_toplevel().unbind(sequence(button, underline))
  
  return enable, disable

enable_traversal_button, disable_traversal_button = traversal_button()


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


def make_name(frame, name):
  if not name: return None
  
  label = ttk.Label(frame, text='%s ' % name)
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
  
  label = ttk.Label(frame, text=' %s' % unit)
  label.grid(row=0, column=2, sticky=tk.E)
  return label


def make_percent(frame):
  WIDTH = 5
  
  label = ttk.Label(frame, width=WIDTH, anchor=tk.CENTER)
  label.grid(row=0, column=2, sticky=tk.E)
  return label


def make_entry(frame, name='', **kwargs):
  frame.rowconfigure(0, weight=1) # make entry vertically centered
  frame.columnconfigure(1, weight=1) # make entry horizontally resizable
  
  entry = ttk.Entry(frame, **kwargs)
  entry.grid(row=0, column=1, sticky=tk.EW)
  return make_name(frame, name), entry


def make_spinbox(frame, name='', wrap=False, unit='', **kwargs):
  frame.rowconfigure(0, weight=1) # make spinbox vertically centered
  frame.columnconfigure(1, weight=1) # make spinbox horizontally resizable
  
  spinbox = ttk.Spinbox(frame, wrap=wrap, **kwargs)
  spinbox.grid(row=0, column=1, sticky=tk.EW)
  return make_name(frame, name), spinbox, make_unit(frame, unit)


def make_combobox(frame, name='', state=None, **kwargs):
  frame.rowconfigure(0, weight=1) # make combobox vertically centered
  frame.columnconfigure(1, weight=1) # make combobox horizontally resizable
  
  combobox = ttk.Combobox(frame, **kwargs)
  combobox.grid(row=0, column=1, sticky=tk.EW)
  
  if state:
    combobox.state(state)
  
  return make_name(frame, name), combobox


def make_scale(frame, name='', variable=None, **kwargs):
  if not variable: variable = tk.IntVar()
  
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
  
  scale.grid(row=0, column=1, sticky=tk.EW)
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


def make_listbox(frame, name='', items=None,
  selectmode=tk.BROWSE, xscroll=False, yscroll=True, **kwargs):
  BG = 'Azure'
  BG2 = 'Azure2'
  
  if not items:
    items = []
  
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
  
  name_frame.columnconfigure(1, weight=1) # make buttons frame column horizontally resizable
  
  # note that this frame uses the pack geometry manager
  # this is to make it possible for the caller
  # to flexibly add more buttons to the left or right side
  buttons_frame = ttk.Frame(name_frame)
  buttons_frame.grid(row=0, column=1, sticky=tk.EW)
  buttons = []
  
  if selectmode == tk.MULTIPLE:
    def select_all():
      listbox.selection_set(0, tk.END)
      listbox.event_generate('<<ListboxSelect>>')
    
    def select_none():
      listbox.selection_clear(0, tk.END)
      listbox.event_generate('<<ListboxSelect>>')
    
    def invert_selection():
      for index in range(listbox.size()):
        if listbox.selection_includes(index):
          listbox.selection_clear(index)
        else:
          listbox.selection_set(index)
      
      listbox.event_generate('<<ListboxSelect>>')
    
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
    
    for button in reversed(buttons):
      button.pack(side=tk.RIGHT, padx=PADX_QW)
  
  return make_name(name_frame, name), (listbox, make_scrollbar(listbox, xscroll, yscroll)
    ), (buttons_frame, buttons)


def progressbar():
  def is_determinate(progressbar):
    return str(progressbar['mode']) == 'determinate'
  
  def configure(widgets, variable, type_):
    progressbar, taskbar = widgets
    variable_set = False
    
    if not type_ in yamosse_progress.types.keys():
      variable.set(int(type_))
      return True
    
    if type_ == yamosse_progress.LOADING:
      if is_determinate(progressbar):
        progressbar['mode'] = 'indeterminate'
        variable.set(0) # must be done after setting mode to take effect
        variable_set = True
        progressbar.start() # as the last step, start the animation
    else:
      if not is_determinate(progressbar):
        progressbar.stop() # as the first step, stop the animation
        progressbar['mode'] = 'determinate'
        variable.set(0) # must be done after setting mode to take effect
        variable_set = True
      
      if type_ == yamosse_progress.DONE:
        variable.set(int(progressbar['maximum']))
        
        if taskbar: taskbar.flash_done()
        return True
      
      if type_ == yamosse_progress.RESET:
        variable.set(0)
        
        if taskbar: taskbar.reset()
        return True
    
    if taskbar: taskbar.set_progress_type(yamosse_progress.types[type_])
    return variable_set
  
  def make(frame, name='', variable=None,
    type_=yamosse_progress.NORMAL, parent=None, task=False, **kwargs):
    if not variable: variable = tk.IntVar()
    
    frame.rowconfigure(0, weight=1) # make progressbar vertically centered
    frame.columnconfigure(1, weight=1) # make progressbar horizontally resizable
    
    percent_label = make_percent(frame)
    
    progressbar = ttk.Progressbar(frame, variable=variable,
      mode='determinate', orient=tk.HORIZONTAL, **kwargs)
    
    progressbar.grid(row=0, column=1, sticky=tk.EW)
    
    taskbar = None
    
    if task and yamosse_progress.PyTaskbar:
      if not parent: parent = frame.winfo_toplevel()
      taskbar = yamosse_progress.PyTaskbar.Progress(hwnd=yamosse_progress.hwnd(parent))
    
    value = 0
    
    def show(name='', index='', mode=''):
      nonlocal value
      
      # only update the percent label in determinate mode
      if is_determinate(progressbar):
        value = variable.get()
        
        if taskbar:
          taskbar.set_progress(value, int(progressbar['maximum']))
      
      text = '%d%%' % value
      percent_label['text'] = text
    
    variable.trace('w', show)
    
    widgets = (progressbar, taskbar)
    if not configure(widgets, variable, type_): show()
    return make_name(frame, name), widgets, percent_label
  
  return configure, make

configure_progressbar, make_progressbar = progressbar()


def make_filedialog(frame, name='', textvariable=None,
  asks=None, parent=None, filetypes=None, **kwargs):
  ASKS_ALL = ('openfilename', 'openfilenames', 'savefilename', 'directory')
  ASKS_FILES = ('openfilename', 'openfilenames', 'savefilename')
  
  if not textvariable: textvariable = tk.StringVar()
  
  frame.rowconfigure(0, weight=1) # make entry vertically centered
  frame.columnconfigure(0, weight=1) # make entry horizontally resizable
  
  entry = ttk.Entry(frame, textvariable=textvariable, **kwargs)
  entry.grid(row=0, sticky=tk.EW)
  
  name_frame = ttk.Frame(frame)
  name_frame.grid(row=1, sticky=tk.EW, pady=PADY_QN)
  
  name_frame.columnconfigure(1, weight=1) # make buttons frame column horizontally resizable
  
  buttons_frame = ttk.Frame(name_frame)
  buttons_frame.grid(row=0, column=1, sticky=tk.EW)
  
  def set_(data):
    if not data:
      return
    
    if isinstance(data, str):
      data = (data,)
    
    textvariable.set(shlex.join(data))
  
  def show(ask='openfilename'):
    filedialog_ask = getattr(filedialog, ''.join(('ask', ask)))
    
    set_(filedialog_ask(parent=parent, filetypes=filetypes
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
    
    buttons.append(button)
  
  # must be done in a separate loop to button creation so tab order is correct
  for button in reversed(buttons):
    button.pack(side=tk.RIGHT, padx=PADX_QW)
  
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
      set_(e.widget.tk.splitlist(e.data))
      return e.action
    
    frame.drop_target_register(tkinterdnd2.DND_FILES)
    frame.dnd_bind('<<DropEnter>>', drop_enter)
    frame.dnd_bind('<<Drop>>', drop)
  
  return make_name(name_frame, name), entry, (buttons_frame, buttons)


def _root_window():
  root_window = None
  
  def get():
    nonlocal root_window
    
    if not root_window:
      root_window = tkdnd.Tk() if tkdnd else tk.Tk()
    
    return root_window
  
  return get

get_root_window = _root_window()


def after_idle_window(window, callback):
  try:
    # for thread safety
    # it's not safe to have a non-GUI thread interact directly with widgets
    # so we queue this for when idle
    window.after_idle(callback)
  except tk.TclError:
    if window.children: raise
    return False
  
  return window.children


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


def release_modal_window(window, destroy=True):
  parent = window.master
  
  # this must be done before destroying the window
  # otherwise the window behind this one will not take focus back
  try:
    parent.attributes('-disabled', False)
  except tk.TclError: pass # not supported on this OS
  
  window.grab_release() # is not necessary on Windows, but is necessary on other OS's
  parent.focus_set()
  if destroy: window.destroy()


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
    
    if resizable:
      window.minsize(*size)
  
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
  style.layout('Borderless.TNotebook', [])
  
  frame = ttk.Frame(window)
  frame.grid(row=0, column=0, sticky=tk.NSEW, padx=PADX_EW, pady=PADY_NS)
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
    elif isinstance(value, bool):
      variable = tk.BooleanVar()
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
  VARIABLE_TYPES = (tk.DoubleVar, tk.BooleanVar, tk.IntVar, tk.StringVar)
  
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