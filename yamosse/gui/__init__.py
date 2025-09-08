import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.font import Font
from collections import namedtuple
from enum import Enum
from weakref import WeakKeyDictionary
import traceback
import threading
from threading import Lock, Event
from contextlib import suppress
from functools import lru_cache
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

PADDING_ALIGN = 2

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

PAD_ALIGN = (PADDING_ALIGN, PADDING_ALIGN)

MINSIZE_ROW_LABELS = 21
MINSIZE_ROW_RADIOBUTTONS = MINSIZE_ROW_LABELS

VALIDATIONOPTIONS = ('validatecommand', 'invalidcommand', 'validate', 'vcmd')

# these default numbers come from the Tk Treeview documentation
DEFAULT_TREEVIEW_ITEM_INDENT = 20
DEFAULT_TREEVIEW_CELL_PADDING = (4, 0)

BINDTAG_MINSIZE = 'minsize'

WINDOWS_ICONPHOTO_BUGFIX = True

IMAGES_DIR = 'images'

VARIABLE_TYPES = {
  bool: tk.BooleanVar,
  int: tk.IntVar,
  float: tk.DoubleVar,
  str: tk.StringVar
}

Widgets = namedtuple('Widgets', ['first', 'middle', 'last'])
Undoable = namedtuple('Undoable', ['undooptions', 'buttons'])


class ImageType(Enum):
  BITMAP = fsenc('Bitmap')
  PHOTO = fsenc('Photo')
  
  def ext(self):
    return type(self)._EXTS[self]

# defined out here so it is a nonmember
# (workaround for Python 3.10)
ImageType._EXTS = {
  ImageType.BITMAP: fsenc('.xbm'),
  ImageType.PHOTO: fsenc('.gif')
}


def _init_report_callback_exception():
  reported = False
  reported_lock = Lock()
  
  tk_report_callback_exception = tk.Tk.report_callback_exception
  
  def report_callback_exception(tk_, exc, val, tb):
    nonlocal reported
    
    tk_report_callback_exception(tk_, exc, val, tb)
    
    with reported_lock:
      if reported: return
      reported = True
    
    with (
      suppress(OSError),
      open('traceback.txt', 'w', encoding='utf8') as file
    ):
      traceback.print_exception(exc, val, tb, file=file)
    
    messagebox.showerror(title='Exception in Tkinter callback',
      message=''.join(traceback.format_exception(exc, val, tb)))
    
    raise val
  
  return report_callback_exception

tk.Tk.report_callback_exception = _init_report_callback_exception()


def state_children_widget(widget, state):
  with suppress(tk.TclError):
    widget['state'] = state
  
  for child in widget.winfo_children():
    state_children_widget(child, state)


def after_invalidcommand_widget(widget, validate):
  # editing a variable from within an invalidcommand normally resets validate to none
  # this ensures it remains set to focusout
  # see: https://www.tcl-lang.org/man/tcl8.5/TkCmd/entry.htm#M7
  widget.after_idle(lambda: widget.configure(validate=validate))


def default_bindtags_widget(widget, name=True, class_=True, window=True, all_=True):
  default_bindtags = []
  
  if name: default_bindtags.append(widget.winfo_name())
  if class_: default_bindtags.append(widget.winfo_class())
  if window: default_bindtags.append(widget.winfo_toplevel())
  if all_: default_bindtags.append(tk.ALL)
  
  return default_bindtags


def bind_truekey_widget(widget, class_='', keysym='',
  press=None, release=None, add=None):
  # disables autorepeat on Linux (X11)
  # https://wiki.tcl-lang.org/page/Disable+autorepeat+under+X11
  state_press = None
  state_release = None
  
  def call_press(e):
    nonlocal state_press
    
    state_press = e.serial
    
    if press and state_press != state_release:
      press(e)
  
  def call_release(e):
    nonlocal state_release
    
    state_release = e.serial
    
    def callback():
      if state_release != state_press:
        release(e)
    
    # this must be after with zero milliseconds, it cannot be after_idle
    # as per the Tk docs, using after with zero milliseconds will
    # schedule for the next round of events, which is what we need here
    # to test if the press/release are paired
    # if we wait until idle, multiple rounds of events will pass
    # and we'll miss our window of opportunity
    if release: widget.after(0, callback)
  
  # the trailing space after the event type is ignored if keysym is empty
  keys = (
    ('<KeyPress %s>' % keysym, call_press),
    ('<KeyRelease %s>' % keysym, call_release)
  )
  
  if class_:
    return [widget.bind_class(class_, s, c, add=add) for s, c in keys]
  
  return [widget.bind(s, c, add=add) for s, c in keys]


def grid_configure_size_widget(widget, configure, **kwargs):
  CONFIGURE = {
    'column': 0,
    'row': 1
  }
  
  getattr(widget, ''.join((configure, 'configure')))(
    tuple(range(widget.grid_size()[CONFIGURE[configure]])), **kwargs)


def padding4_widget(widget, padding):
  with suppress(TypeError):
    padding = widget.tk.splitlist(padding)
  
  if not padding:
    return [0.0, 0.0, 0.0, 0.0]
  
  def fpixels(*lengths):
    return [widget.winfo_fpixels(l) for l in lengths]
  
  # should raise TypeError is padding is just an integer
  with suppress(TypeError):
    # should raise ValueError if too many values to unpack
    try:
      left, top, right, bottom = padding
    except ValueError:
      pass
    else:
      return fpixels(left, top, right, bottom)
    
    try:
      left, vertical, right = padding
    except ValueError:
      pass
    else:
      return fpixels(left, vertical, right, vertical)
    
    try:
      horizontal, vertical = padding
    except ValueError:
      pass
    else:
      return fpixels(horizontal, vertical, horizontal, vertical)
    
    padding, = padding
  
  return fpixels(padding, padding, padding, padding)


def lookup_style_widget(widget, option, element='', state=None, **kwargs):
  style = str(widget['style'])
  
  if not style:
    style = widget.winfo_class()
  
  if element:
    style = '.'.join((style, element))
  
  if state is None:
    with suppress(tk.TclError):
      state = widget.state()
  
  return ttk.Style(widget).lookup(style, option, state=state, **kwargs)


def make_widgets(frame, make_widget, items=None,
  orient=tk.HORIZONTAL, cell=0, sticky=tk.W, padding=PADDING):
  widgets = []
  
  if not items:
    return widgets
  
  ORIENTS = {
    tk.HORIZONTAL: (
      'row',
      'column',
      'padx'
    ),
    
    tk.VERTICAL: (
      'column',
      'row',
      'pady'
    )
  }
  
  # float divide is used for padding in case it is not even
  x, y, pad = ORIENTS[orient]
  last = len(items) - 1
  padding = padding / 2 if last != 0 else 0
  
  # first widget
  widget = make_widget(frame, **items[0])
  widget.grid(sticky=sticky, **{x: cell, y: 0, pad: (0, padding)})
  widgets.append(widget)
  
  # exit if the first widget is the last widget
  if last == 0: return widgets
  
  # middle widgets
  for middle in range(1, last):
    widget = make_widget(frame, **items[middle])
    widget.grid(sticky=sticky, **{x: cell, y: middle, pad: padding})
    widgets.append(widget)
  
  # last widget
  widget = make_widget(frame, **items[last])
  widget.grid(sticky=sticky, **{x: cell, y: last, pad: (padding, 0)})
  widgets.append(widget)
  return widgets


def text_widgets_items(i):
  return [{'text': t} for t in i]


def _traversal_button():
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

enable_traversal_button, disable_traversal_button = _traversal_button()


def link_radiobuttons(radiobuttons, variable):
  radiobuttons = dict(radiobuttons)
  
  def show():
    for w, widget in enumerate(radiobuttons.values()):
      if not widget: continue
      
      normal = w == int(variable.get())
      state_children_widget(widget, tk.NORMAL if normal else tk.DISABLED)
  
  for r, radiobutton in enumerate(radiobuttons.keys()):
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
  return Widgets(make_name(frame, name), entry, None)


def _init_validationoptions_spinbox():
  # the spinbox should always be valid on focusin
  # but we validate on focus so we can save the valid number
  # in case an invalid edit is made and %s is too late to recover it
  VALIDATE = 'focus'
  
  _spinbox_numbers = WeakKeyDictionary()
  
  def invalidcommand(frame):
    def command(W, P, v):
      widget = frame.nametowidget(W)
      
      # we default to zero if the widget has never had a valid value
      # don't use setdefault here because once we clamp, we might end up with a different number
      try:
        number = int(P)
      except ValueError:
        number = _spinbox_numbers.get(widget, 0)
      
      widget.set(yamosse_utils.clamp(
        number,
        int(widget['from']),
        int(widget['to'])
      ))
      
      after_invalidcommand_widget(widget, v)
    
    return frame.register(command), '%W', '%P', '%v'
  
  
  def validatecommand(frame):
    def command(W, P):
      widget = frame.nametowidget(W)
      
      try:
        number = int(P)
      except ValueError:
        return False
      
      valid = str(number) == str(P) and number in range(
        int(widget['from']),
        int(widget['to'])
      )
      
      if valid:
        if widget not in _spinbox_numbers:
          widget.bind(
            '<Destroy>',
            lambda e: _spinbox_numbers.pop(e.widget, None),
            add=True
          )
        
        _spinbox_numbers[widget] = number
      
      return valid
    
    return frame.register(command), '%W', '%P'
  
  def validate(*args, **kwargs):
    return VALIDATE
  
  return {
    'invalidcommand': invalidcommand,
    'validatecommand': validatecommand,
    'validate': validate
  }

validationoptions_spinbox = _init_validationoptions_spinbox()


def make_spinbox(frame, name='', wrap=False, unit='', **kwargs):
  frame.rowconfigure(0, weight=1) # make spinbox vertically centered
  frame.columnconfigure(1, weight=1) # make spinbox horizontally resizable
  
  # we don't want to just define the args to None as default and then use these if they're None
  # because you might actually want no validation
  validation = not yamosse_utils.intersects(kwargs, VALIDATIONOPTIONS)
  
  if validation:
    kwargs |= {o: v(frame) for o, v in validationoptions_spinbox.items()}
  
  spinbox = ttk.Spinbox(frame, wrap=wrap, **kwargs)
  spinbox.grid(row=0, column=1, sticky=tk.EW)
  
  # you can easily call validate yourself if you pass your own validatecommand
  # but if you're relying on the default, we do it, as it's required for the scheme to work
  if validation:
    spinbox.validate()
  
  return Widgets(make_name(frame, name), spinbox, make_unit(frame, unit))


def make_combobox(frame, name='', **kwargs):
  frame.rowconfigure(0, weight=1) # make combobox vertically centered
  frame.columnconfigure(1, weight=1) # make combobox horizontally resizable
  
  combobox = ttk.Combobox(frame, **kwargs)
  combobox.grid(row=0, column=1, sticky=tk.EW)
  return Widgets(make_name(frame, name), combobox, None)


def make_scale(frame, name='', from_=0, to=100, **kwargs):
  frame.rowconfigure(0, weight=1) # make scale vertically centered
  frame.columnconfigure(1, weight=1) # make scale horizontally resizable
  
  # we're using the command here (instead of variable tracing)
  # so that this will continue to work
  # even if the variable the scale is using changes
  showing = False
  scale = None
  percent_label = make_percent(frame)
  
  def show(value):
    nonlocal showing
    
    if showing: return
    
    showing = True
    
    try:
      value = int(value)
      scale.set(value) # this is so we increment in steps instead of a smooth scroll
      percent_label['text'] = '%d%%' % value
    finally:
      showing = False
  
  # I wrote this function before I knew about LabeledScale
  # but I prefer my implementation anyway, so I just kept it
  scale = ttk.Scale(frame,
    from_=from_, to=to, orient=tk.HORIZONTAL,
    command=lambda text: show(float(text)), **kwargs)
  
  scale.grid(row=0, column=1, sticky=tk.EW)
  #scale.bind('<<RangeChanged>>', show)
  
  show(scale.get())
  return Widgets(make_name(frame, name), scale, percent_label)


def make_text(frame, name='', width=10, height=10,
  wrap=tk.WORD, font=None, xscroll=False, yscroll=True, **kwargs):
  FONT = ('Courier', 10)
  
  frame.rowconfigure(1, weight=1) # make scrollbar frame vertically resizable
  frame.columnconfigure(0, weight=1) # make scrollbar frame horizontally resizable
  
  scrollbar_frame = ttk.Frame(frame)
  scrollbar_frame.grid(row=1, sticky=tk.NSEW)
  
  scrollbar_frame.rowconfigure(0, weight=1) # make text vertically resizable
  scrollbar_frame.columnconfigure(0, weight=1) # make text horizontally resizable
  
  text = tk.Text(scrollbar_frame, width=width, height=height,
    wrap=wrap, font=font if font else FONT, **kwargs)
  
  text.grid(row=0, column=0, sticky=tk.NSEW)
  
  return Widgets(
    make_name(frame, name),
    (text, make_scrollbar(text, xscroll, yscroll)),
    None
  )


def _minwidth_treeview():
  default = None
  
  def get(minwidth=None):
    nonlocal default
    
    if minwidth is not None:
      return minwidth
    
    if default is not None:
      return default
    
    return (default := ttk.Treeview().column('#0', 'minwidth'))
  
  return get

get_minwidth_treeview = _minwidth_treeview()


def _item_configurations_treeview(treeview, configuration,
  indent=DEFAULT_TREEVIEW_ITEM_INDENT, item=''):
  tag_configurations = {}
  
  def tags(tags):
    tags = treeview.tk.splitlist(tags)
    
    if not tags:
      return configuration()
    
    font_width = padding_width = image_width = 0.0
    
    for tag in tags:
      tag = str(tag)
      
      try:
        tag_font_width, tag_padding_width, tag_image_width = tag_configurations[tag]
      except KeyError:
        tag_font_width, tag_padding_width, tag_image_width = configuration()
        
        # query the tag's configuration
        # ideally, this would only get the "active" tag
        # but there isn't any way to tell
        # what is the top tag in the stacking order
        # even in the worst case scenario of a conflict though
        # the column will always be wide enough
        try:
          tag_font = str(treeview.tag_configure(tag, 'font'))
        except tk.TclError:
          pass # not supported in this version
        else:
          if tag_font:
            tag_font_width = configuration.measure_font(tag_font)
        
        try:
          tag_padding = str(treeview.tag_configure(tag, 'padding'))
        except tk.TclError:
          pass # not supported in this version
        else:
          if tag_padding:
            tag_padding_width = configuration.measure_padding(tag_padding)
        
        try:
          tag_image = str(treeview.tag_configure(tag, 'image'))
        except tk.TclError:
          pass # not supported in this version
        else:
          if tag_image:
            tag_image_width = configuration.measure_image(tag_image)
        
        tag_configurations[tag] = configuration(
          tag_font_width,
          tag_padding_width,
          tag_image_width
        )
      
      font_width = max(font_width, tag_font_width)
      padding_width = max(padding_width, tag_padding_width)
      image_width = max(image_width, tag_image_width)
    
    return configuration(font_width, padding_width, image_width)
  
  item_configurations = set()
  
  def items(item, indent_width=0.0):
    for child in treeview.get_children(item=item):
      tag_configuration = tags(
        treeview.item(child, 'tags'))
      
      # images and indents occupy the same space
      image_width = indent_width
      
      if (image := treeview.item(child, 'image')):
        image_width += configuration.measure_image(image)
      else:
        image_width += tag_configuration.image_width
      
      item_configurations.add(tag_configuration._replace(
        image_width=image_width
      ))
      
      items(child, indent + indent_width)
  
  items(item)
  return item_configurations


def measure_widths_treeview(treeview, widths):
  # this class must be in here
  # so that the caches are cleared for each call
  class Configuration(namedtuple(
    'Configuration',
    ['font_width', 'padding_width', 'image_width']
  )):
    @classmethod
    @staticmethod
    @lru_cache
    def measure_font(font):
      # cast font descriptors to font objects
      if not isinstance(font, Font):
        font = Font(font=font)
      
      # find average width using '0' character like Tk does
      # see: https://www.tcl-lang.org/man/tcl8.6/TkCmd/text.htm#M21
      return font.measure('0', displayof=treeview)
    
    @classmethod
    @staticmethod
    @lru_cache
    def measure_padding(padding):
      left, top, right, bottom = padding4_widget(treeview, padding)
      return left + right
    
    @classmethod
    @staticmethod
    @lru_cache
    def measure_image(image):
      return treeview.tk.getint(treeview.tk.call('image', 'width', image))
  
  font = str(lookup_style_widget(treeview,
    'font')) or 'TkDefaultFont'
  
  Configuration.__new__.__defaults__ = (
    Configuration.measure_font(font),
    Configuration.measure_padding(DEFAULT_TREEVIEW_CELL_PADDING),
    0.0
  )
  
  kwargs = {}
  
  try:
    kwargs['indent'] = treeview.winfo_fpixels(
      lookup_style_widget(treeview, 'indent'))
  except tk.TclError:
    pass
  
  # this is the set of item configurations
  # will be empty if there are no items
  item_configurations = _item_configurations_treeview(treeview,
    Configuration, **kwargs)
  
  item_padding_width = Configuration.measure_padding(
    lookup_style_widget(treeview, 'padding', element='Item'))
  
  cell_padding_width = Configuration.measure_padding(
    lookup_style_widget(treeview, 'padding', element='Cell'))
  
  # get the per-heading configuration, but only if the heading is shown
  heading_configuration = None
  
  if 'headings' in [str(s) for s in treeview.tk.splitlist(treeview['show'])]:
    font = str(lookup_style_widget(treeview,
      'font', element='Heading')) or font
    
    # the heading padding is added to the treeview padding
    font_width = Configuration.measure_font(font)
    padding_width = Configuration().padding_width + Configuration.measure_padding(
      lookup_style_widget(treeview, 'padding', element='Heading'))
    
    heading_configuration = Configuration(font_width, padding_width)
  
  # measure the widths
  def measure_width(width, font_width, space_width, minwidth=0.0):
    # at least zero, in case space width is greater than minwidth
    return space_width + max(width * font_width, minwidth - space_width, 0.0)
  
  measured_widths = {}
  
  for cid, width in widths.items():
    minwidth = None
    
    # the width can be a sequence like (width, minwidth) which we unpack here
    # if the sequence is too short, just get the width and use default minwidth
    # otherwise the width is specified as an integer, not a sequence
    try:
      width, minwidth = width
    except ValueError:
      width, = width
    except TypeError:
      pass
    
    # a width of None means don't do this column
    if width is None: continue
    
    # we can't just get the minwidth of the current column to use here
    # otherwise, if the minwidth was set to the result of this function
    # then it would stack if this function were called multiple times
    # so here we get the real default
    # this is done after the try block above, because minwidth can be
    # manually specified as None, explicitly meaning
    # to use the default
    minwidth = get_minwidth_treeview(minwidth)
    
    # the element (item/cell) padding is
    # added on top of the treeview/tag (item configuration) padding by Tk
    # so here we do the same
    measured_width = 0.0
    
    if item_configurations:
      if cid == '#0': # item
        # for column #0, we need to worry about indents
        # on top of that, we include the minwidth in the space
        # this is because the indicator has
        # a dynamic width which we can't directly get
        # but it is probably okay to assume it is
        # safely contained in the minwidth
        # (otherwise, it'd get cut off when the column is at its minwidth)
        # so the space width (including the minwidth)
        # is added on top of the text width
        measured_width = max(measure_width(
          width,
          item_configuration.font_width,
          
          (
            item_configuration.image_width
            + item_configuration.padding_width
            + item_padding_width
          ) +
          
          minwidth
        ) for item_configuration in item_configurations)
      else: # cell
        # for all other columns (not #0,) the minimum measured width
        # is the minwidth, but excluding the part of it filled by space
        # this ensures the column won't be smaller
        # than the minwidth (but may be equal to it)
        measured_width = max(measure_width(
          width,
          item_configuration.font_width,
          
          (
            item_configuration.padding_width
            + cell_padding_width
          ),
          
          minwidth
        ) for item_configuration in item_configurations)
    
    if heading_configuration: # heading
      image_width = heading_configuration.image_width
      
      if (heading_image := str(treeview.heading(cid, 'image'))):
        image_width = Configuration.measure_image(heading_image)
      
      measured_width = max(measured_width, measure_width(
        width,
        heading_configuration.font_width,
        image_width + heading_configuration.padding_width,
        minwidth
      ))
    
    # must use ceil here because these widths may be floats
    # and Tk doesn't want a float for the width
    measured_widths[cid] = ceil(measured_width)
  
  return measured_widths


def configure_widths_treeview(treeview, widths):
  measured_widths = measure_widths_treeview(treeview, widths)
  
  for cid, width in measured_widths.items():
    treeview.column(cid, width=width, minwidth=width, stretch=False)


def get_items_treeview(treeview, item=''):
  items = list(treeview.get_children(item=item))
  children = []
  
  for item in items:
    children += get_items_treeview(treeview, item=item)
  
  return items + children


def make_treeview(frame, name='', columns=None, items=None, show=None,
  selectmode=tk.EXTENDED, xscroll=False, yscroll=True, **kwargs):
  columns = yamosse_utils.dict_enumerate(columns) if columns else {}
  
  if show is None:
    show = ['tree', 'headings']
  else:
    show = [str(s) for s in frame.tk.splitlist(show)]
  
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
    
    if column:
      treeview.column(cid, **column)
    
    heading = options.get('heading')
    
    # left align the heading by default
    if not heading:
      heading = {}
    
    heading.setdefault(tk.ANCHOR, tk.W)
    
    treeview.heading(cid, **heading)
  
  def insert(items, parent=''):
    if items is None: return
    
    # items may be a dictionary with custom child IDs
    # or a sequence, where the IDs are auto generated
    for child, insertion in yamosse_utils.dict_enumerate(items).items():
      insertion = insertion.copy() # so we don't modify items dict passed in
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
  buttons = []
  
  if 'tree' in show:
    def expand_all():
      for item in get_items_treeview(treeview):
        treeview.item(item, open=True)
    
    def collapse_all():
      for item in get_items_treeview(treeview):
        treeview.item(item, open=False)
    
    buttons += [
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
    ]
  
  if selectmode == tk.EXTENDED:
    def select_all():
      treeview.selection_set(get_items_treeview(treeview))
    
    treeview.bind('<Control-a>', lambda e: select_all())
    
    def select_none():
      treeview.selection_set(())
    
    treeview.bind('<Control-d>', lambda e: select_none())
    
    def invert_selection():
      treeview.selection_toggle(get_items_treeview(treeview))
    
    treeview.bind('<Control-i>', lambda e: invert_selection())
    
    buttons += [
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
  
  # must be done in a separate loop to button creation so tab order is correct
  for button in reversed(buttons):
    button.pack(side=tk.RIGHT, padx=PADX_QW)
  
  return Widgets(
    make_name(name_frame, name),
    (treeview, make_scrollbar(treeview, xscroll, yscroll)),
    (buttons_frame, buttons)
  )


def heading_text_treeview_columns(c):
  return {cid: {'heading': {'text': t}} for cid, t in yamosse_utils.dict_enumerate(c).items()}


def values_treeview_items(i):
  return {cid: {'values': v} for cid, v in yamosse_utils.dict_enumerate(i).items()}


def make_filedialog(frame, name='',
  asks=None, parent=None, filetypes=None, defaultextension='', **kwargs):
  ASKS_ALL = {
    'openfilename': 'Browse...',
    'openfilenames': 'Browse Files...',
    'saveasfilename': 'Browse...',
    'directory': 'Browse Folder...'
  }
  
  ASKS_FILES = ('openfilename', 'openfilenames', 'saveasfilename')
  
  if asks is None: asks = ('openfilename',)
  
  asks_file = yamosse_utils.intersects(asks, ASKS_FILES)
  asks_dir = 'directory' in asks
  asks_multiple = 'openfilenames' in asks
  
  # we ensure the default extension starts with a period (necessary on Linux)
  if defaultextension:
    defaultextension = yamosse_utils.str_ensureprefix(defaultextension, '.')
  
  frame.rowconfigure(0, weight=1) # make entry vertically centered
  frame.columnconfigure(0, weight=1) # make entry horizontally resizable
  
  entry = ttk.Entry(frame, **kwargs)
  entry.grid(row=0, sticky=tk.EW)
  
  name_frame = ttk.Frame(frame)
  name_frame.grid(row=1, sticky=tk.EW, pady=PADY_QN)
  
  name_frame.columnconfigure(1, weight=1) # make buttons frame column horizontally resizable
  
  buttons_frame = ttk.Frame(name_frame)
  buttons_frame.grid(row=0, column=1, sticky=tk.EW)
  
  def accept(data):
    assert data, 'data must not be empty'
    
    is_str = isinstance(data, str)
    
    if asks_multiple:
      if is_str: data = (data,)
      
      data = shlex.join(data)
    elif not is_str:
      data, = data
      
      assert isinstance(data, str), 'data must be a string or sequence of strings'
    
    entry.delete(0, tk.END)
    entry.insert(tk.END, data)
  
  def show(ask='openfilename'):
    kwargs = {}
    
    if filetypes and ask != 'directory':
      kwargs['filetypes'] = filetypes
    
    if defaultextension and ask == 'saveasfilename':
      kwargs['defaultextension'] = defaultextension
    
    data = getattr(filedialog, ''.join(('ask', ask)))(
      parent=parent, **kwargs)
    
    if not data:
      return
    
    accept(data)
  
  buttons = [ttk.Button(
    buttons_frame,
    text=ASKS_ALL[ask],
    command=lambda ask=ask: show(ask)
  ) for ask in asks]
  
  # must be done in a separate loop to button creation so tab order is correct
  for button in reversed(buttons):
    button.pack(side=tk.RIGHT, padx=PADX_QW)
  
  # drag and drop
  if tkinterdnd2:
    def refuse(data):
      assert data, 'data must not be empty'
      
      multiple = len(data) > 1
      
      # if multiple selection is not enabled, refuse multiple files
      if multiple and not asks_multiple:
        return True
      
      not_asks_dir = multiple or not asks_dir
      
      for d in data:
        if not asks_file and os.path.isfile(d):
          return True
        
        if not_asks_dir and os.path.isdir(d):
          return True
      
      return False
    
    frame.drop_target_register(tkinterdnd2.DND_FILES)
    
    def drop_enter(e):
      data = [str(d) for d in e.widget.tk.splitlist(e.data)]
      
      # on some platforms we only get data on drop
      # but if we do have data, refuse it now
      # so we can show the "not allowed sign"
      if data and refuse(data):
        return tkinterdnd2.REFUSE_DROP
      
      entry.focus_set()
      entry.selection_range(0, tk.END)
      return e.action
    
    frame.dnd_bind('<<DropEnter>>', drop_enter)
    
    def drop_leave(e):
      entry.selection_clear()
      return e.action
    
    frame.dnd_bind('<<DropLeave>>', drop_leave)
    
    def drop(e):
      data = [str(d) for d in e.widget.tk.splitlist(e.data)]
      
      entry.selection_clear()
      
      if not data or refuse(data):
        frame.bell() # to make it more obvious the file was noticed but refused
        return tkinterdnd2.REFUSE_DROP
      
      accept(data)
      return e.action
    
    frame.dnd_bind('<<Drop>>', drop)
  
  return Widgets(make_name(name_frame, name), entry, (buttons_frame, buttons))


def make_undoable(frame):
  WIDTH = 6
  
  undoing = False
  
  def undo(command):
    nonlocal undoing
    
    undoing = True
    
    try:
      revert = command[0]
      revert(*command[1:])
    finally:
      undoing = False
  
  # https://wiki.tcl-lang.org/page/Undo+and+Redo+undoable+widgets
  undoings = [] # list of undoable things - each is a 2 part list
          # first the arguments to undo the operation;
          # then the arguments to redo the operation.
  redoings = [] # list of redoable things - copy of those undoings which have been undone.
  
  undo_button = None
  redo_button = None
  
  def enable():
    undo_button['state'] = tk.NORMAL if undoings else tk.DISABLED
    redo_button['state'] = tk.NORMAL if redoings else tk.DISABLED
  
  def undooptions(undodata, dodata): # save undooptions sufficient to undo and redo an action
    if not undoing:
      # store state before and after event change.
      #for un in undoings: print(f'Undo:: {un}')
      
      # not in an undo so save event.
      undoings.append((undodata, dodata))
      redoings.clear()
      
      enable()
    else:
      #print(f'In undo dont save event {args}')
      pass
  
  def undolast(): # undoes last undoable operation.
    if not undoings:
      print('No more undoable events')
      return
    
    undothis = undoings.pop()
    undo(undothis[0])
    
    redoings.append(undothis)
    
    enable()
  
  def redolast():
    if not redoings: return
    
    redothis = redoings.pop()
    undo(redothis[1])
    #frame.update_idletasks()
    
    undoings.append(redothis)
    
    enable()
  
  photo_images = get_root_images()[ImageType.PHOTO]
  
  undo_button = ttk.Button(frame, text='Undo', width=WIDTH,
    image=photo_images[fsenc('undo.gif')], compound=tk.LEFT,
    command=undolast, state=tk.DISABLED)
  
  undo_button.grid(row=0, column=0)
  
  redo_button = ttk.Button(frame, text='Redo', width=WIDTH,
    image=photo_images[fsenc('redo.gif')], compound=tk.LEFT,
    command=redolast, state=tk.DISABLED)
  
  redo_button.grid(row=0, column=1, padx=PADX_QW)
  
  window = frame.winfo_toplevel()
  window.bind('<Control-z>', lambda e: undolast())
  window.bind('<Control-y>', lambda e: redolast())
  return Undoable(undooptions, (undo_button, redo_button))


def _init_root_window():
  root_window = None
  
  local = threading.local()
  
  def styles():
    # the order of the fillstates must be reversed for priority levels
    PROGRESS_ORIENTS = ('Horizontal', 'Vertical')
    PROGRESS_FILLSTATES = [s.value for s in reversed(yamosse_progress.State)]
    
    style = ttk.Style()
    
    style.theme_settings('default', {
      'Treeview.Heading': {
        'configure': {'padding': (2, 0)}
      }
    })
    
    for orient in PROGRESS_ORIENTS:
      style.layout(
        f'{orient}.Fill.TProgressbar',
        style.layout(f'{orient}.TProgressbar')
      )
    
    # suppressed in case this is not supported for this platform or version
    with suppress(tk.TclError):
      for o, orient in enumerate(PROGRESS_ORIENTS):
        fill_progressbar = f'{orient}.Fill.Progressbar'
        
        style.element_create(
          f'{fill_progressbar}.trough',
          'vsapi', 'PROGRESS',
          o + 1
        )
        
        style.element_create(
          f'{fill_progressbar}.pbar',
          'vsapi', 'PROGRESS',
          o + 5, PROGRESS_FILLSTATES,
          width=11, height=11
        )
      
      style.theme_settings('vista', {
        'Horizontal.Fill.TProgressbar': {
          'layout': [
            ('Horizontal.Fill.Progressbar.trough', {
              'children': [('Horizontal.Fill.Progressbar.pbar', {
                'side': tk.LEFT,
                'sticky': tk.NS
              })]
            }),
          ]
        },
        
        'Vertical.Fill.TProgressbar': {
          'layout': [
            ('Vertical.Fill.Progressbar.trough', {
              'children': [('Vertical.Fill.Progressbar.pbar', {
                'side': tk.BOTTOM,
                'sticky': tk.EW
              })]
            }),
          ]
        }
      })
    
    style.configure('Debug.TFrame', background='red', relief=tk.GROOVE)
    style.configure('Title.TLabel', font=('Trebuchet MS', 24))
    
    style.layout('Raised.TNotebook', [])
    style.configure('Raised.TNotebook > .TFrame', relief=tk.RAISED)
    
    # the align element ensures that all buttons are large enough
    # to fit a 16x16 icon
    style.element_create('align', 'image',
      get_root_images()[ImageType.BITMAP][fsenc('align.xbm')])
    
    layout = style.layout('TButton')
    elements = elements_layout(layout, 'Button.padding')
    
    for element in elements:
      children = element.setdefault('children', [])
      children.append(('align', {}))
    
    style.layout('TButton', layout)
  
  def get():
    nonlocal root_window
    
    if root_window:
      return root_window
    
    root_window = tkdnd.Tk() if tkdnd else tk.Tk()
    
    local.owner = True
    styles()
    return root_window
  
  def owner():
    return getattr(local, 'owner', False)
  
  return get, owner

get_root_window, owner_root_window = _init_root_window()


def _init_minsize_window():
  binding = None
  
  # we can't know a window's width and height until it is viewable
  def viewable(widget, map_=False):
    if not widget.winfo_viewable():
      raise ValueError('widget must be viewable')
    
    if map_:
      bindtags = list(widget.bindtags())
      bindtags.remove(BINDTAG_MINSIZE)
      widget.bindtags(bindtags)
    
    widget.minsize(widget.winfo_width(), widget.winfo_height())
  
  def minsize_window(window):
    nonlocal binding
    
    try:
      viewable(window)
    except ValueError:
      if not binding:
        binding = get_root_window().bind_class(
          BINDTAG_MINSIZE,
          '<Map>',
          lambda e: viewable(e.widget, map_=True)
        )
      
      bindtags = window.bindtags()
      if BINDTAG_MINSIZE in bindtags: return
      window.bindtags((BINDTAG_MINSIZE,) + window.bindtags())
  
  return minsize_window

minsize_window = _init_minsize_window()


def _init_sizegrip_window():
  sizegrips = WeakKeyDictionary()
  
  def sizegrip_window(window, sizegrip=None):
    if sizegrip:
      if window not in sizegrips:
        window.bind_class(bindtag_window(window),
          '<Destroy>', lambda e: sizegrips.pop(e.widget, None), add=True)
      
      sizegrips[window] = sizegrip
    else:
      sizegrip = sizegrips[window]
    
    xresizable, yresizable = window.resizable()
    
    if xresizable and yresizable:
      sizegrip.grid(row=2, column=2, sticky=tk.SE)
    else:
      sizegrip.grid_remove()
  
  return sizegrip_window

sizegrip_window = _init_sizegrip_window()


def after_window(window, callback):
  # for thread safety
  # it's not safe to have a non-GUI thread interact directly with widgets
  # so we need to use window.after with a callback
  # here I use the window.children property to check if the window exists
  # I prefer this over winfo_exists because it means we don't hit
  # the interpreter, which may not be running anymore
  # which is also why we check the children first before calling window.after
  # (technically a race but unlikely to cause issues, window.after would probably throw anyway)
  # but it does make the assumption
  # that the window will have at least one child
  # which it will, if make_window was used to make it
  # it's important to stash the children variable before use
  # so another thread doesn't change it underneath us before we return it
  if not (children := window.children):
    return children
  
  try:
    # we use after(0) here instead of after_idle
    # because this is basically akin to other events getting sent
    # in the sense that it'll be handled on the next round of event processing
    window.after(0, callback)
  except (tk.TclError, RuntimeError):
    # silence any errors caused by the window exiting
    # before getting the chance to run our callback
    # otherwise it's probably a genuine error so reraise it then
    if not (children := window.children):
      return children
    
    raise
  
  return window.children


def after_wait_window(window, callback):
  # don't deadlock if we're on the GUI thread
  if owner_root_window():
    if children := window.children:
      callback()
    
    return children
  
  # the same as after_window, except
  # we block until the callback has finished running
  event = Event()
  
  def set_():
    try:
      return callback()
    finally:
      event.set()
  
  if not (children := after_window(window, set_)):
    return children
  
  event.wait()


def bindtag_window(window):
  # create a bindtag which will only get events specifically for this window
  window_bindtag = bindtag(window)
  bindtags = window.bindtags()
  
  if window_bindtag not in bindtags:
    window.bindtags((window_bindtag,) + window.bindtags())
  
  return window_bindtag


def bind_buttons_window(window, ok_button=None, cancel_button=None):
  for name in ('<Return>', '<Escape>'):
    window.unbind(name)
  
  if ok_button:
    if window is not ok_button.winfo_toplevel():
      raise ValueError('ok_button window mismatch')
    
    ok_button['default'] = tk.ACTIVE
    window.bind('<Return>', lambda e: ok_button.invoke())
  
  if cancel_button:
    if window is not cancel_button.winfo_toplevel():
      raise ValueError('cancel_button window mismatch')
    
    cancel_button['default'] = tk.NORMAL
    window.bind('<Escape>', lambda e: cancel_button.invoke())


def release_modal_window(window, close='destroy'):
  parent = window.master
  
  if not parent:
    raise ValueError('window must be a child window')
  
  # this must be done before destroying the window
  # otherwise the window behind this one will not take focus back
  # suppressed in case this is not supported on this OS
  with suppress(tk.TclError):
    parent.attributes('-disabled', False)
  
  window.grab_release() # is not necessary on Windows, but is necessary on other OS's
  parent.focus_set()
  
  if close:
    getattr(window, close)()


def set_modal_window(window, delete_window=release_modal_window):
  parent = window.master
  
  if not parent:
    raise ValueError('window must be a child window')
  
  # call the release function when the close button is clicked
  window.protocol('WM_DELETE_WINDOW', lambda: delete_window(window))
  
  # make the window behind us play the "bell" sound if we try and interact with it
  # suppressed in case this is not supported on this OS
  with suppress(tk.TclError):
    parent.attributes('-disabled', True)
  
  # turns on WM_TRANSIENT_FOR on Linux (X11) which modal dialogs are meant to have
  # this should be done before setting the window type to dialog
  # see https://tronche.com/gui/x/icccm/sec-4.html#WM_TRANSIENT_FOR
  window.transient()
  
  # disable the minimize and maximize buttons
  # Windows
  with suppress(tk.TclError):
    window.attributes('-toolwindow', True)
  
  # Linux (X11)
  # see type list here:
  # https://specifications.freedesktop.org/wm-spec/latest/ar01s05.html#id-1.6.7
  with suppress(tk.TclError):
    window.attributes('-type', 'dialog')
  
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
  
  try:
    xresizable, yresizable = resizable
  except TypeError:
    xresizable, yresizable = resizable, resizable
  
  window.resizable(xresizable, yresizable)
  
  if size:
    window.geometry('%dx%d+%d+%d' % (size + location) if location else '%dx%d' % size)
  
  # give the window a sizegrip
  # (should be done after setting new window geometry)
  sizegrip_window(window)
  
  if iconphotos:
    if window is get_root_window():
      # in this case make this the default icon
      # note that it is still necessary to call iconphoto before this
      # because Windows has a bug where you need to call iconphoto with default off first
      # otherwise it will use the wrong icon size
      if WINDOWS_ICONPHOTO_BUGFIX:
        window.iconphoto(False, *iconphotos)
      
      window.iconphoto(True, *iconphotos)
    else:
      window.iconphoto(False, *iconphotos)


def make_window(window, make_frame, args=None, kwargs=None):
  for child in list(window.children.values()):
    with suppress(tk.TclError):
      child.destroy()
  
  window.rowconfigure(1, weight=1) # make frame vertically resizable
  window.columnconfigure(1, weight=1) # make frame horizontally resizable
  
  sizegrip = ttk.Sizegrip(window)
  minsize = max(PADDING, sizegrip.winfo_reqwidth(), sizegrip.winfo_reqheight())
  
  window.rowconfigure((0, 2), minsize=minsize)
  window.columnconfigure((0, 2), minsize=minsize)
  
  sizegrip_window(window, sizegrip=sizegrip)
  
  frame = ttk.Frame(window)
  frame.grid(row=1, column=1, sticky=tk.NSEW)
  
  assert window.children, 'window must have children'
  
  args, kwargs = yamosse_utils.arguments(args, kwargs)
  return window, make_frame(frame, *args, **kwargs)


def _root_images():
  root_images = None
  
  def get():
    nonlocal root_images
    
    if root_images:
      return root_images
    
    def scandir(path, callback):
      result = {}
      
      with os.scandir(path) as scandir:
        for scandir_entry in scandir:
          item = callback(scandir_entry)
          
          if not item:
            continue
          
          key, value = item
          result[key] = value
      
      return result
    
    def callback_image(entry, make_image, ext):
      name = entry.name.lower() # intentionally NOT casefold - could merge two files to one
      
      if entry.is_dir():
        return (name, scandir(entry.path, lambda image_entry: callback_image(
          image_entry, make_image, ext)))
      
      # ensure it has the expected file extension so we don't trip on a Thumbs.db or something
      if os.path.splitext(name)[1] != ext:
        return None
      
      try:
        return (name, make_image(file=fsdec(entry.path)))
      except tk.TclError:
        return None
    
    def callback_image_type(entry):
      if not entry.is_dir():
        return None
      
      image = entry.name.title()
      
      try:
        type_ = ImageType(image)
      except ValueError:
        return None
      
      return (type_, scandir(entry.path, lambda image_entry: callback_image(
        image_entry, getattr(tk, ''.join((fsdec(image), 'Image'))), type_.ext())))
    
    # getting root window needs to be done first
    # to avoid popping an empty window in some circumstances
    # all names/paths here are encoded with fsenc so that they will be compared by ordinal
    root_window = get_root_window()
    root_images = scandir(fsenc(yamosse_root.root(IMAGES_DIR)), callback_image_type)
    
    # this is done to prevent exceptions
    # in case the application dies on a thread that isn't the GUI thread
    # normally the images would have their __del__ method called
    # only to discover that the Tk interpreter isn't running
    def destroy(e):
      nonlocal root_images
      
      root_images = None
    
    root_window.bind_class(bindtag_window(root_window),
      '<Destroy>', destroy, add=True)
    
    return root_images
  
  return get

get_root_images = _root_images()


def elements_layout(layout, name):
  elements = []
  
  for child, options in layout:
    if str(child) == name:
      elements.append(options)
    
    try:
      children = options['children']
    except KeyError:
      continue
    
    elements += elements_layout(children, name)
  
  return elements


def get_variables_from_attrs(attrs):
  # this prevents Tkinter from popping an empty window
  # if we haven't created the root window yet
  get_root_window()
  
  variable = None
  variables = {}
  
  for key, value in vars(attrs).items():
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


def copy_attrs_to_variables(variables, attrs):
  for key, value in variables.items():
    if isinstance(value, tuple(VARIABLE_TYPES.values())):
      value.set(getattr(attrs, key))
      continue
    
    variables[key] = getattr(attrs, key)


def set_attrs_to_variables(variables, attrs):
  for key, value in variables.items():
    if isinstance(value, tuple(VARIABLE_TYPES.values())):
      setattr(attrs, key, value.get())
      continue
    
    setattr(attrs, key, value)


def enter_stack(stack, widget):
  # it is possible to recieve more than one Enter event before Leave event
  # (on comboboxes)
  # so we must check if this is the same widget as the one on top of the stack
  if stack and stack[-1] is widget:
    return False
  
  stack.append(widget)
  return True


def leave_stack(stack):
  if not stack:
    return False
  
  stack.pop()
  return True


def threaded():
  if not tk.Tcl().eval('set tcl_platform(threaded)'):
    raise NotImplementedError('Non-threaded builds are not supported.')


def bindtag(obj):
  # this is prefixed to ensure the string doesn't start with a period (.) character
  # which would indicate this is a widget, not a bindtag
  return ''.join(('bindtag', repr(id(obj))))


def gui(make_frame, window=None, child=False, args=None, kwargs=None):
  if not window:
    window = get_root_window()
  
  return make_window(
    window if not child else tk.Toplevel(window),
    make_frame,
    args=args,
    kwargs=kwargs
  )