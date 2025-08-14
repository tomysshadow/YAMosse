import re
from weakref import WeakSet
from os import fsencode as fsenc

import yamosse.utils as yamosse_utils

from .. import gui

RE_NATURAL = re.compile(r'(\d+)')

_treeviews = WeakSet()


# uses "natural" sorting - the values being sorted here are often numbers
# https://nedbatchelder.com/blog/200712/human_sorting.html
def _key_natural(value):
  return [yamosse_utils.try_int(v) for v in RE_NATURAL.split(value)]


def _key_child(item):
  return _key_natural(item[0])


def _key_value(item):
  return _key_natural(item[1])


def treeview_sorted(treeview):
  if treeview in _treeviews:
    raise RuntimeError('treeview_sorted is single shot per-treeview')
  
  # this can't use dict_once because items may be removed from it over time
  _treeviews.add(treeview)
  
  table_sort_icons = gui.get_root_images()[gui.FSENC_BITMAP][fsenc('table sort icons')]
  sort_both_small = table_sort_icons[fsenc('sort_both_small.xbm')]
  sort_up_small = table_sort_icons[fsenc('sort_up_small.xbm')]
  sort_down_small = table_sort_icons[fsenc('sort_down_small.xbm')]
  
  # swaps between three sorting states for each heading: both, down, and up
  # in the both state (the default,) columns are sorted by their ID
  # in the down and up states, items are sorted forward and reversed, respectively
  def show(cid=None, reverse=False):
    key = _key_child if cid is None else _key_value
    
    def move(item=''):
      children = dict.fromkeys(treeview.get_children(item=item))
      
      for child in children:
        if key is _key_value:
          children[child] = treeview.set(child, cid)
        
        move(item=child)
      
      children = yamosse_utils.dict_sorted(children, key=key, reverse=reverse)
      
      # rearrange items in sorted positions
      for index, child in enumerate(children):
        treeview.move(child, item, index)
    
    move()
    
    for column in treeview['columns']:
      treeview.heading(
        column,
        image=sort_both_small,
        command=lambda column=column: show(cid=column)
      )
    
    treeview.bind(
      '<<SortedTreeviewShow>>',
      lambda e, reverse=reverse: show(cid=cid, reverse=reverse)
    )
    
    if key is _key_value:
      image = sort_up_small if reverse else sort_down_small
      reverse = not reverse
      
      # reverse sort next time
      treeview.heading(
        cid,
        image=image,
        command=lambda: show(cid=cid if reverse else None, reverse=reverse)
      )
  
  show()