import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
from contextlib import suppress
from abc import ABC, abstractmethod
from functools import cache, lru_cache
from collections import namedtuple
from math import ceil

from .. import gui

# these default numbers come from the Tk Treeview documentation
DEFAULT_TREEVIEW_ITEM_INDENT = 20
DEFAULT_TREEVIEW_CELL_PADDING = (4, 0)


@cache
def get_treeview_minwidth():
  return ttk.Treeview().column('#0', 'minwidth')


def _treeview_item_configurations(configuration, treeview,
  indent=DEFAULT_TREEVIEW_ITEM_INDENT, item=''):
  tag_configurations = {}
  
  def tags(tags):
    tags = gui.strsplitlist_widget(treeview, tags)
    
    if not tags:
      return configuration()
    
    font_width = padding_width = image_width = 0.0
    
    for tag in tags:
      try:
        tag_font_width, tag_padding_width, tag_image_width = tag_configurations[tag]
      except KeyError:
        # query the tag's configuration
        # ideally, this would only get the "active" tag
        # but there isn't any way to tell
        # what is the top tag in the stacking order
        # even in the worst case scenario of a conflict though
        # the column will always be wide enough
        tag_font_width, tag_padding_width, tag_image_width = configuration()
        
        try:
          tag_font = treeview.tag_configure(tag, 'font')
        except tk.TclError:
          pass # not supported in this version
        else:
          if tag_font:
            tag_font_width = configuration.measure_font(tag_font)
        
        try:
          tag_padding = treeview.tag_configure(tag, 'padding')
        except tk.TclError:
          pass # not supported in this version
        else:
          if tag_padding:
            tag_padding_width = configuration.measure_padding(tag_padding)
        
        try:
          tag_image = treeview.tag_configure(tag, 'image')
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
      tag_configuration = tags(treeview.item(child, 'tags'))
      
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


def measure_treeview_widths(widths, treeview):
  def strsplittuple(func):
    # this decorator ensures hashability, for use by lru_cache
    return lambda t: func(tuple(gui.strsplitlist_widget(treeview, t)))
  
  # this class must be in here
  # so that the caches are cleared for each call
  class Configuration(ABC):
    def __hash__(self):
      # hash differently depending on what class we are
      return hash((repr(id(type(self))), tuple(self)))
    
    @abstractmethod
    def measure_cid(self, cid, width, minwidth):
      pass
    
    @staticmethod
    def measure_width(width, font_width, space_width, minwidth=0.0):
      # at least zero, in case space width is greater than minwidth
      return space_width + max(width * font_width, minwidth - space_width, 0.0)
    
    @staticmethod
    @strsplittuple
    @lru_cache
    def measure_font(font):
      # cast font description to font object
      # then find average width using '0' character like Tk does
      # see: https://www.tcl-lang.org/man/tcl8.6/TkCmd/text.htm#M21
      return Font(font=font).measure('0', displayof=treeview)
    
    @staticmethod
    @strsplittuple
    @lru_cache
    def measure_padding(padding):
      left, top, right, bottom = gui.padding4_widget(treeview, padding)
      return left + right
    
    @staticmethod
    @strsplittuple
    @lru_cache
    def measure_image(image):
      # it's possible to specify multiple images for different states
      # the first image determines the width
      # other image states are padded to fit the width of the first image
      return treeview.tk.getint(treeview.tk.call('image', 'width', image[0]))
  
  def lookup_style(style, element=None):
    return gui.lookup_style_widget(treeview, style, element=element)
  
  item_padding_width = Configuration.measure_padding(
    lookup_style('padding', element='Item'))
  
  cell_padding_width = Configuration.measure_padding(
    lookup_style('padding', element='Cell'))
  
  default_cell_padding_width = Configuration.measure_padding(
    DEFAULT_TREEVIEW_CELL_PADDING)
  
  class ItemConfiguration(Configuration, namedtuple(
    'ItemConfiguration',
    ['font_width', 'padding_width', 'image_width'],
    
    defaults=(
      Configuration.measure_font(
        lookup_style('font') or ('TkDefaultFont',)),
      
      default_cell_padding_width,
      0.0
    )
  )):
    __slots__ = () # prevents mutation on object (namedtuple meant to be immutable)
    
    def measure_cid(self, cid, width, minwidth):
      # the element (item/cell) padding is
      # added on top of the treeview/tag (item configuration) padding by Tk
      # so here we do the same
      if cid == '#0':
        # for column #0, we need to worry about indents
        # on top of that, we include the minwidth in the space
        # this is because the indicator has
        # a dynamic width which we can't directly get
        # but it is probably okay to assume it is
        # safely contained in the minwidth
        # (otherwise, it'd get cut off when the column is at its minwidth)
        # so the space width (including the minwidth)
        # is added on top of the text width
        return self.measure_width(
          width,
          self.font_width,
          
          (
            self.image_width
            + self.padding_width
            + item_padding_width
          ) +
          
          minwidth
        )
      
      # for all other columns (not #0,) the minimum measured width
      # is the minwidth, but excluding the part of it filled by space
      # this ensures the column won't be smaller
      # than the minwidth (but may be equal to it)
      return self.measure_width(
        width,
        self.font_width,
        
        (
          self.padding_width
          + cell_padding_width
        ),
        
        minwidth
      )
  
  # the heading padding is added to the default cell padding
  class HeadingConfiguration(Configuration, namedtuple(
    'HeadingConfiguration',
    ['font_width', 'padding_width', 'image_width'],
    
    defaults=(
      Configuration.measure_font(
        lookup_style('font', element='Heading') or ('TkHeadingFont',)),
      
      default_cell_padding_width + Configuration.measure_padding(
        lookup_style('padding', element='Heading')),
      
      0.0
    )
  )):
    __slots__ = () # prevents mutation on object (namedtuple meant to be immutable)
    
    def measure_cid(self, cid, width, minwidth):
      space_width = self.padding_width
      
      if (image := treeview.heading(cid, 'image')):
        space_width += self.measure_image(image)
      else:
        space_width += self.image_width
      
      return self.measure_width(width, self.font_width, space_width, minwidth)
  
  kwargs = {}
  
  with suppress(tk.TclError):
    kwargs['indent'] = treeview.winfo_fpixels(
      lookup_style('indent'))
  
  # this is the set of configurations
  # will be empty here if there are no items
  configurations = _treeview_item_configurations(ItemConfiguration,
    treeview, **kwargs)
  
  # add the heading configuration, but only if the heading is shown
  if 'headings' in gui.strsplitlist_widget(treeview, treeview['show']):
    configurations.add(HeadingConfiguration())
  
  # measure the widths
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
    if width is None:
      continue
    
    # we can't just get the minwidth of the current column to use here
    # otherwise, if the minwidth was set to the result of this function
    # then it would stack if this function were called multiple times
    # so we use get_treeview_minwidth to get the real default
    # this is done after the try block above, because minwidth can be
    # manually specified as None, explicitly meaning
    # to use the default
    if minwidth is None:
      minwidth = get_treeview_minwidth()
    
    # must use ceil here because these widths may be floats
    # and Tk doesn't want a float for the width
    measured_widths[cid] = ceil(max(
      configuration.measure_cid(
        cid,
        width,
        minwidth
      ) for configuration in configurations
    ) if configurations else 0.0)
  
  return measured_widths


def treeview_widths(widths, treeview):
  measured_widths = measure_treeview_widths(widths, treeview)
  
  for cid, width in measured_widths.items():
    treeview.column(cid, width=width, minwidth=width, stretch=False)