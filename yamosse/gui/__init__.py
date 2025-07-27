import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.font import Font
import traceback
from threading import Lock
import re
from math import ceil
import shlex
import os
from os import fsencode as fsenc
from os import fsdecode as fsdec

try:
  import tkinterdnd2
  import tkinterdnd2.TkinterDnD as tkdnd
except ImportError:
  tkinterdnd2 = None
  tkdnd = None

import yamosse.root as yamosse_root
import yamosse.utils as yamosse_utils
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

DEFAULT_MINWIDTH = -1

# these default numbers come from the Tk Treeview documentation
DEFAULT_TREEVIEW_INDENT = 20
DEFAULT_TREEVIEW_CELL_PADDING = (4, 0)

WINDOWS_ICONPHOTO_BUGFIX = True

IMAGES_DIR = 'images'

FSENC_BITMAP = fsenc('Bitmap')
FSENC_PHOTO = fsenc('Photo')

VARIABLE_TYPES = {
  bool: tk.BooleanVar,
  int: tk.IntVar,
  float: tk.DoubleVar,
  str: tk.StringVar
}


def _init_report_callback_exception():
  reported = False
  reported_lock = Lock()
  
  tk_report_callback_exception = tk.Tk.report_callback_exception
  
  def report_callback_exception(tk, exc, val, tb):
    nonlocal reported
    nonlocal reported_lock
    
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

_init_report_callback_exception()


def fpixels_widget(widget, lengths):
  return [widget.winfo_fpixels(l) for l in lengths]


def padding4_widget(widget, padding):
  padding = yamosse_utils.try_split(padding)
  if not padding: return [0.0, 0.0, 0.0, 0.0]
  
  # should raise TypeError is padding is just an integer
  try:
    # should raise ValueError if too many values to unpack
    try: left, top, right, bottom = padding
    except ValueError: pass
    else: return fpixels_widget(widget, (left, top, right, bottom))
    
    try: left, vertical, right = padding
    except ValueError: pass
    else: return fpixels_widget(widget, (left, vertical, right, vertical))
    
    try: horizontal, vertical = padding
    except ValueError: pass
    else: return fpixels_widget(widget, (horizontal, vertical, horizontal, vertical))
    
    padding, = padding
  except TypeError: pass
  return fpixels_widget(widget, (padding, padding, padding, padding))


def padding2_widget(widget, padding):
  left, top, right, bottom = padding4_widget(widget, padding)
  return [left + right, top + bottom]


def enable_widget(widget, enabled=True, cursor=True):
  try: widget['state'] = tk.NORMAL if enabled else tk.DISABLED
  except tk.TclError: pass
  else:
    # we do this in the try-else block
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
  
  for child_widget in widget.winfo_children():
    enable_widget(child_widget, enabled=enabled, cursor=cursor)


def prevent_default_widget(widget, class_=False, window=True, all_=True):
  bindtags = [widget]
  if class_: bindtags.append(widget.winfo_class())
  if window: bindtags.append(widget.winfo_toplevel())
  if all_: bindtags.append(tk.ALL)
  
  widget.bindtags(bindtags)


def lookup_style_widget(widget, option, element='', state=None, **kwargs):
  style = widget['style']
  
  if not style:
    style = widget.winfo_class()
  
  if element:
    style = '.'.join((style, element))
  
  try:
    if not state:
      state = widget.state()
  except tk.TclError: pass
  
  return ttk.Style(widget).lookup(style, option, state=state, **kwargs)


def measure_text_width_widget(widget, width, font):
  # cast font descriptors to font objects
  if not isinstance(font, Font):
    font = Font(font=font)
  
  # find average width using '0' character like Tk does
  # see: https://www.tcl-lang.org/man/tcl8.6/TkCmd/text.htm#M21
  return width * font.measure('0', displayof=widget)


def make_widgets(frame, make_widget, names,
  orient=tk.HORIZONTAL, cell=0, sticky=tk.W, padding=PADDING, **kwargs):
  ORIENTS = (tk.HORIZONTAL, tk.VERTICAL)
  
  if not orient in ORIENTS: raise ValueError('orient must be in %r' % (ORIENTS,))
  
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
  widget.grid(sticky=sticky, **{x: cell, y: 0, pad: (0, padding)})
  widgets.append(widget)
  
  # exit if the first widget is the last widget
  if last == 0: return widgets
  
  # middle widgets
  for middle in range(last - 1):
    widget = make_widget(frame, text=names[middle], **kwargs)
    widget.grid(sticky=sticky, **{x: cell, y: middle, pad: padding})
    widgets.append(widget)
  
  # last widget
  widget = make_widget(frame, text=names[last], **kwargs)
  widget.grid(sticky=sticky, **{x: cell, y: last, pad: (padding, 0)})
  widgets.append(widget)
  return widgets


def _traversal_button():
  def sequence(button, underline):
    assert underline >= 0, 'underline must be greater than or equal to zero'
    return '<Alt-%c>' % str(button['text'])[underline].lower()
  
  def enable(button):
    underline = int(button['underline'])
    if underline < 0: return
    
    button.winfo_toplevel().bind(
      sequence(button, underline),
      lambda e: button.focus_set()
    )
  
  def disable(button):
    underline = int(button['underline'])
    if underline < 0: return
    
    button.winfo_toplevel().unbind(sequence(button, underline))
  
  return enable, disable

enable_traversal_button, disable_traversal_button = _traversal_button()


def link_radiobuttons(radiobuttons, variable):
  radiobuttons = dict(radiobuttons)
  
  widgets = tuple(radiobuttons.values())
  radiobuttons = tuple(radiobuttons.keys())
  
  def show():
    for w, widget in enumerate(widgets):
      if not widget: continue
      
      enabled = (w == variable.get())
      enable_widget(widget, enabled=enabled)
  
  for r, radiobutton in enumerate(radiobuttons):
    radiobutton.configure(value=r, variable=variable, command=show)
  
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
  
  if state: combobox.state(state)
  return make_name(frame, name), combobox


def make_scale(frame, name='', variable=None,
  from_=0, to=100, **kwargs):
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
    from_=from_, to=to, orient=tk.HORIZONTAL, command=show, **kwargs)
  
  scale.grid(row=0, column=1, sticky=tk.EW)
  show()
  return make_name(frame, name), scale, percent_label


def delete_lines_text(text, max_lines=1000):
  lines = text.index(tk.END)
  lines = int(lines[:lines.index('.')]) - max_lines
  
  if lines > 0: text.delete('1.0', '%d.%s' % (lines, tk.END))


def make_text(frame, name='', width=10, height=10,
  autoseparators=False, wrap=tk.WORD, font=None, xscroll=False, yscroll=True, **kwargs):
  FONT = ('Courier', 10)
  
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


def _embed():
  CLASS_TEXT = 'Text'
  
  VIEWS = {
    '<<PrevChar>>': (tk.X, (tk.SCROLL, -1, tk.UNITS)),
    '<<NextChar>>': (tk.X, (tk.SCROLL, 1, tk.UNITS)),
    '<<PrevLine>>': (tk.Y, (tk.SCROLL, -1, tk.UNITS)),
    '<<NextLine>>': (tk.Y, (tk.SCROLL, 1, tk.UNITS))
  }
  
  # a regex that handles text substitutions in scripts
  # that properly handles escaped (%%) substitutions (which str.replace would not)
  RE_SCRIPT = re.compile('%(.)')
  
  def insert(text, widget, line=0):
    # width for the widget needs to be set explicitly, not by its geometry manager
    widget.pack_propagate(False)
    widget.grid_propagate(False)
    
    text['state'] = tk.NORMAL
    
    try:
      # if the placeholder exists, then delete it
      try: text.delete(text.embed)
      except tk.TclError: pass
      
      # use the insertion cursor so that it moves from the linestart to the lineend
      text.mark_set(tk.INSERT,
        '%d.0' % line if line > 0 else '%s - %d lines' % (tk.END, -line))
      
      # if there is anything before us on the line, insert a newline
      if text.compare(tk.INSERT, '>', '%s linestart' % tk.INSERT):
        text.insert(tk.INSERT, '\n')
      
      # actual magic happens here
      text.window_create(tk.INSERT, window=widget, stretch=True)
      
      # if there is anything after us on the line, insert a newline
      if text.compare(tk.INSERT, '<', '%s lineend' % tk.INSERT):
        text.insert(tk.INSERT, '\n')
    finally:
      text['state'] = tk.DISABLED
  
  def configure(e):
    widget = e.widget
    
    # set the width of the children to fill the available space
    for child in widget.winfo_children():
      inset = widget['borderwidth'] + widget['highlightthickness'] + widget['padx']
      child['width'] = e.width - (inset * 2)
  
  stack = []
  
  def enter(e):
    widget = e.widget
    
    if stack and stack[-1] == widget: return
    stack.append(widget)
  
  def leave(e):
    if not stack: return
    stack.pop()
  
  def peek(M):
    # if some other widget has already handled this event
    # then don't do anything
    if not int(M):
      while stack:
        text = stack[-1]
        
        # we're just giving the text widget a "vibe check" here to test it's still alive
        try: text.winfo_toplevel()
        except tk.TclError: pass
        else: return text
        
        # throw out dead text
        stack.pop()
    
    return ''
  
  def root():
    root = None
    
    def get():
      nonlocal root
      
      if not root:
        # there's a bunch of stuff we only want to do once
        # but we need the interpreter to be running to do it
        # i.e. there needs to be a root window
        # so all of that stuff is done in here
        root_window = get_root_window()
        tk_ = root_window.tk
        
        W = root_window.register(peek)
        repl_W = lambda match: f'${W}' if match.group(1) == 'W' else match.group()
        
        def focus(*args):
          # allow getting focus, prevent setting focus
          if len(args) == 1: return ''
          return tk_.call('interp', 'invokehidden', '', 'focus', *args)
        
        focus_cbname = root_window.register(focus)
        
        def view(widget, name):
          view, args = VIEWS[name]
          
          getattr(root_window.nametowidget(widget), ''.join((view, 'view')))(*args)
        
        view_cbname = root_window.register(view)
        
        window_binds = set()
        
        def bind(*args):
          # if we are binding a new script to the Text class
          # propagate it to all the text embed widgets
          try: class_, name, script = args
          except ValueError: pass
          else:
            # note: we'd have to do name.removeprefix('+') if VIEWS contained non-virtual events
            # but since they are virtual, you can't use + with them anyway
            if str(class_) == CLASS_TEXT and not name in VIEWS.keys():
              for window_bind in window_binds:
                window_bind(name, script)
          
          return tk_.call('interp', 'invokehidden', '', 'bind', *args)
        
        tk_.call('interp', 'hide', '', 'bind')
        tk_.call('interp', 'alias', '', 'bind', '', root_window.register(bind))
        
        root = (W, repl_W, focus_cbname, view_cbname, window_binds)
      
      return root
    
    return get
  
  get_root = root()
  
  def text(text):
    if str(text.winfo_class()) != CLASS_TEXT: raise ValueError('text must have class Text')
    
    try:
      if text.embed: raise RuntimeError('text_embed is single shot per-text')
    except AttributeError: pass
    
    # doubles as a placeholder to prevent text selection
    text.embed = ttk.Frame(text)
    embed = text.embed
    
    text['state'] = tk.NORMAL
    
    try:
      # we don't use enable_widget here as we don't actually want that
      # (it would disable any child widgets within the text)
      # it should not take focus until an event is fired (it hoards the focus otherwise)
      # it shouldn't have a border, there's a bug where the embedded widgets appear over top of it
      # (put a border around the surrounding frame instead)
      text.configure(takefocus=False, cursor='',
        bg=lookup_style_widget(embed, 'background'), borderwidth=0)
      
      # unbind from Text class so we can't get duplicate events
      # they'll be received from window instead
      prevent_default_widget(text)
      
      text.bind('<Configure>', configure)
      
      text.bind('<Enter>', enter)
      text.bind('<Leave>', leave)
      
      # delete anything that might've been typed in before the text was passed to us
      # then create the placeholder frame
      text.delete('1.0', tk.END)
      text.window_create(tk.END, window=embed, stretch=True)
    finally:
      text['state'] = tk.DISABLED
    
    W, repl_W, focus_cbname, view_cbname, window_binds = get_root()
    
    window = text.winfo_toplevel()
    tk_ = window.tk
    
    bindings = {}
    
    def window_bind(name, script):
      if not bindings: window_binds.add(window_bind)
      
      # here is the problem this tries to solve
      # usually, events are only sent to the
      # specific widgets that have focus, or that the mouse is over, depending on the event
      # so if you are over a Frame, Label, etc. the Text just won't get <MouseWheel> events
      # similarly for Arrow Keys, Page Up/Page Down, etc.
      # because the Text widget does not have focus, it doesn't get them
      # but I want it to scroll as long as the mouse is over it, and any of these things happen
      # and I don't want to just redefine those bindings myself, they're all platform specific
      # bindtags don't solve this problem, all of these default behaviours are part of
      # the Text class, but if we bind the children to the Text class, nothing happens because
      # the Text class default bindings need the Text widget to be the recipient of the event
      # (i.e., the value of e.widget in the event handler is wrong)
      # so we want to "forward" or "retrigger" the event, from an arbitrary widget
      # to the Text widget, so we get that sweet default behaviour for all those keys
      # so we bind to window, which always gets these events
      # thanks to the default bindtags of the child widgets
      # (and we DON'T use bind_all - we only want events if the window's focused anyway)
      # but what then?
      # event_generate isn't sufficient because we can't just give it the Event object from Tkinter
      # (i.e. the one with e.widget, e.num, e.keysym, e.delta etc.)
      # all the values on the Event object undergo subtle transformations
      # when it enters Python from Tk, so it's a lossy process and we can't go back the other way
      # and either way, it still has the problem of sending the event to the wrong place
      # because of focus not being set correctly
      # and trying to restore focus back to a state it was in previously is a fool's errand
      # to do this properly, we can't go Tk > Python, this needs to happen entirely Tk side
      # that way text substitutions (like %b, %N, %D...) remain intact
      # the default bindings get their original values, as they are expecting
      # and we can replace the widget that actually got the event (the window we bound to)
      # with the Text widget we want
      # since %W is just a text substitution normally anyway, so find and replace
      # and that way, the Text widget can get these events, even without focus!
      # it even properly handles cases where the event was already swallowed by another widget
      # i.e. you press arrow keys on a Scale, so the text doesn't scroll, in that case...
      # and, you can still use Tab to traverse the interface too!
      # the only weirdness is the text widget default bindings will usually focus the text widget
      # even if takefocus is False (unlike most other widgets,) so we need to specifically
      # disable the focus command, temporarily, by aliasing it, and then restore it back after
      # and that way, clicking random places in the window
      # won't ever give the text focus, it is completely impossible for it to steal away the focus
      bindings[name] = window.bind(name,
        
        f'''set {W} [{W} %M]
        if {{${W} == ""}} {{ continue }}
        
        interp hide {{}} focus
        interp alias {{}} focus {{}} {focus_cbname}
        catch {{{RE_SCRIPT.sub(repl_W, script)}}} result options
        
        interp alias {{}} focus {{}}
        interp expose {{}} focus
        return -options $options $result'''
      )
    
    def window_unbind():
      if not bindings: return
      window_binds.discard(window_bind)
      
      # try to clean up the window bindings
      # but since this could happen at any old time
      # (who knows when we might decide to garbage collect this object?)
      # make sure to handle the case where window is already dead
      try:
        for name, binding in bindings.items():
          window.unbind(name, binding)
      except (tk.TclError, RuntimeError): pass
      
      bindings.clear()
    
    def text_bind():
      window_unbind()
      
      names = list(tk_.call('bind', CLASS_TEXT))
      
      # this first loop is just necessary because
      # we want to make the arrow keys scroll instantly
      # default behaviour is to move the text marker, which
      # will eventually scroll, but only when it hits the bottom of the screen
      # this is the only instance where we want to forego the Text class defaults
      for name in VIEWS.keys():
        try: names.remove(name)
        except ValueError: pass
        
        window_bind(name, f'{view_cbname} %W {name}')
      
      for name in names:
        window_bind(name, tk_.call('bind', CLASS_TEXT, name))
    
    try: text_del = text.__del__
    except AttributeError: text_del = lambda: None
    
    def text_unbind():
      try: text_del()
      finally: window_unbind()
    
    text.__del__ = text_unbind
    text_bind()
  
  return insert, text

insert_embed, text_embed = _embed()


def _minwidth_treeview():
  default = DEFAULT_MINWIDTH
  
  def get(minwidth=DEFAULT_MINWIDTH):
    nonlocal default
    
    if minwidth != DEFAULT_MINWIDTH:
      return minwidth
    
    if default == DEFAULT_MINWIDTH:
      default = ttk.Treeview().column('#0', 'minwidth')
    
    return default
  
  return get

get_minwidth_treeview = _minwidth_treeview()


def indents_treeview(treeview, item=None):
  if item is None: return 0
  
  def parent():
    nonlocal item
    
    # must check for empty string specifically (zero should fall through)
    item = str(treeview.parent(item))
    return item != ''
  
  indents = 0
  while parent(): indents += 1
  return indents


def measure_widths_treeview(treeview, widths, item=None):
  # get the per-treeview indent, padding and font
  indent = lookup_style_widget(treeview, 'indent')
  try: indent = treeview.winfo_fpixels(indent)
  except tk.TclError: indent = DEFAULT_TREEVIEW_INDENT
  
  padding_width = padding2_widget(treeview, DEFAULT_TREEVIEW_CELL_PADDING)[0]
  
  font = lookup_style_widget(treeview, 'font')
  assert font, 'font must not be empty'
  
  fonts = {font}
  
  # get the per-heading font, but only if the heading is shown
  show = yamosse_utils.try_split(treeview['show'])
  show_headings = True
  
  try: show = [str(s) for s in show]
  except TypeError: pass
  else:
    show_headings = 'headings' in show
    
    if show_headings:
      font = lookup_style_widget(treeview, 'font', element='Heading')
      if font: fonts.add(font)
  
  def width_image(name):
    return int(treeview.tk.call('image', 'width', name)) if name else 0
  
  item_image_width = 0
  
  # get the per-tag padding, fonts, and images
  tags = {}
  
  for child in treeview.get_children(item=item):
    child_tags = yamosse_utils.try_split(treeview.item(child, 'tags'))
    
    for child_tag in child_tags:
      # first check if we've already done this tag before
      # although it doesn't take very long to query a tag's configuration, it is still
      # worth checking if we've done it yet, as it is likely there are many many columns
      # but only a few tags they are collectively using
      tags_len = len(tags)
      if tags.setdefault(child_tag, tags_len) != tags_len: continue
      
      # after confirming we have not done the tag yet, query the tag's configuration
      # ideally, this would only get the "active" tag
      # but there isn't any way to tell what is the top tag in the stacking order
      # even in the worst case scenario of a conflict though, the column will always be wide enough
      try:
        padding = treeview.tag_configure(child_tag, 'padding')
      except tk.TclError:
        pass # not supported in this version
      else:
        padding_width = max(padding_width, padding2_widget(treeview, padding)[0])
      
      try:
        font = treeview.tag_configure(child_tag, 'font')
      except tk.TclError:
        pass # not supported in this version
      else:
        if font: fonts.add(font)
      
      try:
        image = treeview.tag_configure(child_tag, 'image')
      except tk.TclError:
        pass # not supported in this version
      else:
        item_image_width = max(item_image_width, width_image(image))
    
    # get the per-item image
    item_image_width = max(item_image_width,
      width_image(treeview.item(child, 'image')))
  
  # get the per-element (item/cell) padding
  item_padding_width = padding2_widget(treeview,
    lookup_style_widget(treeview, 'padding', element='Item'))[0]
  
  cell_padding_width = padding2_widget(treeview,
    lookup_style_widget(treeview, 'padding', element='Cell'))[0]
  
  # measure the widths
  measured_widths = {}
  
  for cid, width in widths.items():
    minwidth = DEFAULT_MINWIDTH
    
    # the width can be a sequence like (width, minwidth) which we unpack here
    # if the sequence is too short, just get the width and use default minwidth
    # otherwise the width is specified as an integer, not a sequence
    try: width, minwidth = width
    except ValueError: width, = width
    except TypeError: pass
    
    # a width of None means don't do this column
    if width is None: continue
    
    # we can't just get the minwidth of the current column to use here
    # otherwise, if the minwidth was set to the result of this function
    # then it would stack if this function were called multiple times
    # so here we get the real default
    # this is done after the try block above, because minwidth can be
    # manually specified as DEFAULT_MINWIDTH, explicitly meaning to use the default
    minwidth = get_minwidth_treeview(minwidth)
    
    # get the per-heading image, but only if the heading is shown
    heading_image_width = width_image(treeview.heading(cid, 'image')) if show_headings else 0
    
    # the element (item/cell) padding is added on top of the treeview/tag padding by Tk
    # so here we do the same
    # for column #0, we need to worry about indents
    # on top of that, we include the minwidth in the space width
    # this is because the indicator has a dynamic width which we can't directly get
    # but it is probably okay to assume it is safely contained in the minwidth
    # (otherwise, it'd get cut off when the column is at its minwidth)
    # so the space width (including the minwidth) is added on top of the text width
    # for all other columns (not #0,) minimum text width is the minwidth, but excluding
    # the part of it filled by space width
    # this ensures the column won't be smaller than the minwidth (but may be equal to it)
    # if the space width fills the entire minwidth, this is undesirable for the measured result
    # so in that case, the text width is, in effect, initially zero
    space_width = padding_width
    text_width = 0
    
    if cid == '#0':
      space_width += item_padding_width + max(item_image_width, heading_image_width) + minwidth + (
        indent * indents_treeview(treeview, item=item))
    else:
      space_width += cell_padding_width + heading_image_width
      text_width = max(text_width, minwidth - space_width)
    
    # get the text width for the font that would take up the most space in the column
    for font in fonts:
      text_width = max(text_width, measure_text_width_widget(treeview, width, font))
    
    # must use ceil here because these widths may be floats; Tk doesn't want a float for the width
    measured_widths[cid] = ceil(space_width + text_width)
  
  return measured_widths


def configure_widths_treeview(treeview, *args, **kwargs):
  measured_widths = measure_widths_treeview(treeview, *args, **kwargs)
  
  for cid, width in measured_widths.items():
    treeview.column(cid, width=width, minwidth=width, stretch=False)


def make_treeview(frame, name='', columns=None, items=None, show=None,
  selectmode=tk.BROWSE, xscroll=False, yscroll=True, **kwargs):
  columns = yamosse_utils.dict_enumerate(columns) if columns else {}
  show = ('tree', 'headings') if show is None else [str(s) for s in yamosse_utils.try_split(show)]
  
  frame.rowconfigure(0, weight=1) # make scrollbar frame vertically resizable
  frame.columnconfigure(0, weight=1) # make scrollbar frame horizontally resizable
  
  scrollbar_frame = ttk.Frame(frame)
  scrollbar_frame.grid(row=0, sticky=tk.NSEW)
  
  scrollbar_frame.rowconfigure(0, weight=1) # make treeview vertically resizable
  scrollbar_frame.columnconfigure(0, weight=1) # make treeview horizontally resizable
  
  treeview = ttk.Treeview(scrollbar_frame,
    columns=tuple(columns.keys()), selectmode=selectmode, show=show, **kwargs)
  
  treeview.grid(row=0, column=0, sticky=tk.NSEW)
  
  for cid, options in columns.items():
    # we don't set a default value for get
    # (it's valid for column/heading to be explicitly set to None, so pointless anyway)
    column = options.get('column')
    if column: treeview.column(cid, **column)
    
    heading = options.get('heading')
    
    # left align the heading by default
    if not heading: heading = {}
    heading.setdefault(tk.ANCHOR, tk.W)
    
    treeview.heading(cid, **heading)
  
  def insert(items, parent=''):
    if items is None: return
    
    # items may be a dictionary with custom child IDs
    # or a sequence, where the IDs are auto generated
    for child, insertion in yamosse_utils.dict_enumerate(items).items():
      children = insertion.pop('children', None)
      
      treeview.insert(parent, tk.END, child, **insertion)
      insert(children, parent=child)
  
  insert(items)
  
  name_frame = ttk.Frame(frame)
  name_frame.grid(row=1, sticky=tk.EW, pady=PADY_QN)
  
  name_frame.columnconfigure(1, weight=1) # make buttons frame column horizontally resizable
  
  # note that this frame uses the pack geometry manager
  # this is to make it possible for the caller
  # to flexibly add more buttons to the left or right side
  buttons_frame = ttk.Frame(name_frame)
  buttons_frame.grid(row=0, column=1, sticky=tk.EW)
  buttons = ()
  
  def get_items(item=''):
    items = treeview.get_children(item=item)
    
    for item in items:
      items += get_items(item=item)
    
    return items
  
  if 'tree' in show:
    def expand_all():
      for item in get_items():
        treeview.item(item, open=True)
    
    def collapse_all():
      for item in get_items():
        treeview.item(item, open=False)
    
    buttons += (
      ttk.Button(
        buttons_frame,
        text='Expand All',
        command=expand_all
      ),
        
      ttk.Button(
        buttons_frame,
        text='Collapse All',
        command=collapse_all
      )
    )
  
  if selectmode == tk.EXTENDED:
    def select_all():
      treeview.selection_set(get_items())
    
    def select_none():
      treeview.selection_set(())
    
    def invert_selection():
      treeview.selection_toggle(get_items())
    
    buttons += (
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
    )
  
  for button in reversed(buttons):
    button.pack(side=tk.RIGHT, padx=PADX_QW)
  
  return make_name(name_frame, name), (treeview, make_scrollbar(treeview, xscroll, yscroll)
    ), (buttons_frame, buttons)


def heading_text_columns(c):
  return {cid: {'heading': {'text': t}} for cid, t in yamosse_utils.dict_enumerate(c).items()}


def values_items(i):
  return {cid: {'values': v} for cid, v in yamosse_utils.dict_enumerate(i).items()}


def _sorted():
  RE_NATURAL = re.compile(r'(\d+)')
  
  # uses "natural" sorting - the values being sorted here are often numbers
  # https://nedbatchelder.com/blog/200712/human_sorting.html
  def key_natural(value):
    return [yamosse_utils.try_int(v) for v in RE_NATURAL.split(value)]
  
  def key_child(item):
    return key_natural(item[0])
  
  def key_value(item):
    return key_natural(item[1])
  
  def treeview(treeview):
    try:
      if treeview.sorted: raise RuntimeError('treeview_sorted is single shot per-treeview')
    except AttributeError: pass
    
    treeview.sorted = True
    
    table_sort_icons = get_root_images()[FSENC_BITMAP][fsenc('table sort icons')]
    sort_both_small = table_sort_icons[fsenc('sort_both_small.xbm')]
    sort_up_small = table_sort_icons[fsenc('sort_up_small.xbm')]
    sort_down_small = table_sort_icons[fsenc('sort_down_small.xbm')]
    
    # swaps between three sorting states for each heading: both, down, and up
    # in the both state (the default,) columns are sorted by their ID
    # in the down and up states, items are sorted forward and reversed, respectively
    def show(cid=None, reverse=False):
      key = key_child if cid is None else key_value
      
      def move(item=''):
        children = dict.fromkeys(treeview.get_children(item=item))
        
        for child in children.keys():
          if key is key_value:
            children[child] = treeview.set(child, cid)
          
          move(item=child)
        
        children = yamosse_utils.dict_sorted(children, key=key, reverse=reverse)
        
        # rearrange items in sorted positions
        for index, child in enumerate(children.keys()):
          treeview.move(child, item, index)
      
      move()
      
      for column in treeview['columns']:
        treeview.heading(
          column,
          image=sort_both_small,
          command=lambda column=column: show(cid=column)
        )
      
      if key is key_value:
        image = sort_up_small if reverse else sort_down_small
        
        # reverse sort next time
        treeview.heading(
          cid,
          image=image,
          command=lambda: show(cid=None if reverse else cid, reverse=not reverse)
        )
    
    show()
  
  return treeview

treeview_sorted = _sorted()


def _progressbar():
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

configure_progressbar, make_progressbar = _progressbar()


def make_filedialog(frame, name='', textvariable=None,
  asks=None, parent=None, filetypes=None, defaultextension='', **kwargs):
  ASKS_ALL = ('openfilename', 'openfilenames', 'saveasfilename', 'directory')
  ASKS_FILES = ('openfilename', 'openfilenames', 'saveasfilename')
  
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
    if not data: return
    if isinstance(data, str): data = (data,)
    
    textvariable.set(shlex.join(data))
  
  def show(ask='openfilename'):
    kwargs = {}
    
    if filetypes and ask != 'directory':
      kwargs['filetypes'] = filetypes
    
    if defaultextension and ask == 'saveasfilename':
      kwargs['defaultextension'] = defaultextension
    
    set_(getattr(filedialog, ''.join(('ask', ask)))(parent=parent, **kwargs))
  
  if asks == None: asks = ('openfilename',)
  
  buttons = []
  
  for ask in asks:
    if not ask in ASKS_ALL: raise ValueError('ask must be in %r' % (ASKS_ALL,))
    
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
      if not data: return tkinterdnd2.REFUSE_DROP
      if isinstance(data, str): data = (data,)
      
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
  # for thread safety
  # it's not safe to have a non-GUI thread interact directly with widgets
  # so we queue this for when idle
  try: window.after_idle(callback)
  except (tk.TclError, RuntimeError):
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
  try: parent.attributes('-disabled', False)
  except tk.TclError: pass # not supported on this OS
  
  window.grab_release() # is not necessary on Windows, but is necessary on other OS's
  parent.focus_set()
  if destroy: window.destroy()


def set_modal_window(window, delete_window=release_modal_window):
  # call the release function when the close button is clicked
  window.protocol('WM_DELETE_WINDOW', lambda: delete_window(window))
  
  # make the window behind us play the "bell" sound if we try and interact with it
  try: window.master.attributes('-disabled', True)
  except tk.TclError: pass # not supported on this OS
  
  # turns on WM_TRANSIENT_FOR on Linux (X11) which modal dialogs are meant to have
  # this should be done before setting the window type to dialog
  # see https://tronche.com/gui/x/icccm/sec-4.html#WM_TRANSIENT_FOR
  window.transient()
  
  # disable the minimize and maximize buttons
  # Windows
  try: window.attributes('-toolwindow', True)
  except tk.TclError: pass # not supported on this OS
  
  # Linux (X11)
  # see type list here: https://specifications.freedesktop.org/wm-spec/latest/ar01s05.html#id-1.6.7
  try: window.attributes('-type', 'dialog')
  except tk.TclError: pass # not supported on this OS
  
  # wait for window to be visible
  # (necessary on Linux, does nothing on Windows but it doesn't matter there)
  window.wait_visibility()
  
  # bring window to front, focus it, and prevent interacting with window behind us
  window.lift()
  window.focus_set()
  window.grab_set()


def location_center_window(parent, size):
  width, height = size
  
  return (
    parent.winfo_x() + (parent.winfo_width() / 2) - (width / 2),
    parent.winfo_y() + (parent.winfo_height() / 2) - (height / 2)
  )


def customize_window(window, title, resizable=True, size=None, location=None, iconphotos=None):
  window.title(title)
  window.resizable(resizable, resizable)
  
  if size:
    window.geometry('%dx%d+%d+%d' % (size + location) if location else '%dx%d' % size)
    
    if resizable:
      window.minsize(*size)
  
  # should be done after setting new window geometry
  window.show_sizegrip(resizable)
  
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
  window.rowconfigure(1, weight=1) # make frame vertically resizable
  window.columnconfigure(1, weight=1) # make frame horizontally resizable
  
  sizegrip = ttk.Sizegrip(window)
  minsize = max(PADDING, sizegrip.winfo_reqwidth(), sizegrip.winfo_reqheight())
  
  window.rowconfigure((0, 2), minsize=minsize)
  window.columnconfigure((0, 2), minsize=minsize)
  
  def show_sizegrip(resizable=True):
    if resizable:
      sizegrip.grid(row=2, column=2, sticky=tk.SE)
    else:
      sizegrip.grid_remove()
  
  window.show_sizegrip = show_sizegrip
  show_sizegrip()
  
  style = ttk.Style(window)
  style.configure('Debug.TFrame', background='Red', relief=tk.GROOVE)
  style.configure('Title.TLabel', font=('Trebuchet MS', 24))
  
  style.layout('Borderless.TNotebook', [])
  style.configure('Borderless.TNotebook > .TFrame', relief=tk.RAISED)
  
  frame = ttk.Frame(window)
  frame.grid(row=1, column=1, sticky=tk.NSEW)
  return window, make_frame(frame, *args, **kwargs)


def _root_images():
  root_images = None
  
  def get():
    nonlocal root_images
    
    # this prevents Tkinter from popping an empty window if we haven't created the root window yet
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
        name = entry.name.lower() # intentionally NOT casefold - could merge two files to one
        
        if entry.is_dir():
          return (name, scandir(entry.path, lambda image_entry: callback_image(
            image_entry, make_image)))
        
        try: return (name, make_image(file=fsdec(entry.path)))
        except tk.TclError: return None
      
      def callback_images(entry):
        if not entry.is_dir(): return None
        
        image = entry.name.title()
        
        return (image, scandir(entry.path, lambda image_entry: callback_image(
          image_entry, getattr(tk, ''.join((fsdec(image), 'Image'))))))
      
      # all names/paths here are encoded with fsenc so that they will be compared by ordinal
      root_images = scandir(fsenc(yamosse_root.root(IMAGES_DIR)), callback_images)
    
    return root_images
  
  return get

get_root_images = _root_images()


def get_variables_from_object(object_):
  # this prevents Tkinter from popping an empty window if we haven't created the root window yet
  get_root_window()
  
  variable = None
  variables = {}
  
  for key, value in vars(object_).items():
    for object_type, variable_type in VARIABLE_TYPES.items():
      if isinstance(value, object_type):
        variable = variable_type()
        break
    else:
      variables[key] = value
      continue
    
    variable.set(value)
    variables[key] = variable
  
  return variables


def set_variables_to_object(variables, object_):
  for key, value in variables.items():
    if isinstance(value, tuple(VARIABLE_TYPES.values())):
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