import tkinter as tk
from tkinter import ttk
import re
from weakref import WeakKeyDictionary

from .. import gui

BINDTAG = 'embed'
CLASS_TEXT = 'Text'

VIEWS = {
  '<<PrevChar>>': (tk.X, (tk.SCROLL, -1, tk.UNITS)),
  '<<NextChar>>': (tk.X, (tk.SCROLL, 1, tk.UNITS)),
  '<<PrevLine>>': (tk.Y, (tk.SCROLL, -1, tk.UNITS)),
  '<<NextLine>>': (tk.Y, (tk.SCROLL, 1, tk.UNITS)),
  '<<PrevWord>>': (tk.X, (tk.SCROLL, -10, tk.UNITS)),
  '<<NextWord>>': (tk.X, (tk.SCROLL, 10, tk.UNITS)),
  '<<PrevPara>>': (tk.Y, (tk.SCROLL, -10, tk.UNITS)),
  '<<NextPara>>': (tk.Y, (tk.SCROLL, 10, tk.UNITS))
}

ADD = '+'

# a regex that finds text substitutions in scripts
# that properly handles escaped (%%) substitutions (which str.replace would not)
RE_SCRIPT = re.compile('%(.)')

_stack = []
_texts = WeakKeyDictionary()
_windows = WeakKeyDictionary()


def insert_embed(text, widget, line=0):
  # width for the widget needs to be set explicitly, not by its geometry manager
  widget.pack_propagate(False)
  widget.grid_propagate(False)
  
  text['state'] = tk.NORMAL
  
  try:
    # if the placeholder exists, then delete it
    try:
      text.delete(_texts[text])
    except tk.TclError:
      pass
    
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


def _peek_embed(M):
  # if some other widget has already handled this event
  # then don't do anything
  stack = _stack if not int(M) else None
  
  while stack:
    text = stack[-1]
    
    if text.winfo_exists():
      return text
    
    # throw out dead text
    stack.pop()
  
  return ''


def _root_embed():
  root = None
  
  def get():
    nonlocal root
    
    if root: return root
    
    # there's a bunch of stuff we only want to do once
    # but we need the interpreter to be running to do it
    # i.e. there needs to be a root window
    # so all of that stuff is done in here
    root_window = gui.get_root_window()
    
    def configure(e):
      widget = e.widget
      
      inset = sum(widget.winfo_fpixels(widget[i]) for i in (
        'borderwidth', 'highlightthickness', 'padx'))
      
      width = max(0, widget.winfo_fpixels(e.width) - (inset * 2))
      
      # set the width of the children to fill the available space
      for child in widget.winfo_children():
        child['width'] = width
    
    root_window.bind_class(BINDTAG, '<Configure>', configure, add=True)
    
    def enter(e):
      widget = e.widget
      
      if _stack and _stack[-1] is widget:
        return
      
      _stack.append(widget)
    
    root_window.bind_class(BINDTAG, '<Enter>', enter, add=True)
    
    def leave(e):
      if not _stack:
        return
      
      _stack.pop()
    
    root_window.bind_class(BINDTAG, '<Leave>', leave, add=True)
    
    tk_ = root_window.tk
    
    def bind(*args):
      return tk_.call('interp', 'invokehidden', '', 'bind', *args)
    
    W = root_window.register(_peek_embed)
    
    def repl_W(match):
      return f'${W}' if match.group(1) == 'W' else match.group()
    
    def focus(*args):
      # allow getting focus, prevent setting focus
      if len(args) == 1: return ''
      return tk_.call('interp', 'invokehidden', '', 'focus', *args)
    
    focus_cbname = root_window.register(focus)
    
    def view(widget, name):
      view, args = VIEWS[name]
      
      getattr(root_window.nametowidget(widget), ''.join((view, 'view')))(*args)
    
    view_cbname = root_window.register(view)
    
    name_sequence_bindtag = None
    
    def name_sequence(sequence):
      # we need to get the "canonical" name from the sequence
      # sequences can have multiple forms that are considered equivalent
      # for example, '<KeyPress-a>' and 'a' refer to the same event
      # for the purpose of storing them in a dictionary, we need
      # to squash these inconsistencies
      # we could try and parse the string ourselves, but why leave it to guesswork
      # it's easier to just create a dummy binding so Tk translates the sequence
      # for us, into a canonical name, then get the name
      # the bindtag here is intended to be unique to this function
      # so that only one event will be bound to it at a time
      bind(name_sequence_bindtag, sequence, ' ')
      
      # get the name, which should be the only binding
      # then unbind the sequence
      try:
        name, = bind(name_sequence_bindtag)
      finally:
        bind(name_sequence_bindtag, sequence, '')
      
      return str(name)
    
    name_sequence_bindtag = gui.bindtag(name_sequence)
    
    def bind_window(window_bindings, name):
      window, bindings = window_bindings
      
      # we always need to do the main script
      scripts = bindings.setdefault(name, [])
      
      if not scripts:
        # back up the binding that was already on the window before
        # we get this binding from Tk, so it shouldn't begin with a + prefix
        script = bind(window, name)
        assert not script.startswith(ADD), 'script must not be prefixed with %r' % ADD
        
        scripts.append(''.join((ADD, script)))
      
      # we want to make the arrow keys scroll instantly
      # default behaviour is to move the text marker, which
      # will eventually scroll, but only when it hits the bottom of the screen
      # this is the only instance where we want to forego the Text class defaults
      if name in VIEWS:
        script = f'{view_cbname} %W {name}'
      else:
        # note: the scripts are *not* stripped of leading/trailing whitespace
        # a + after a space is not interpreted as a prefix
        script = bind(CLASS_TEXT, name)
        assert not script.startswith(ADD), 'script must not be prefixed with %r' % ADD
      
      # this is how we "forward" the event from the window to an arbitrary text widget
      # so that we can get the scrolling behaviour of the default bindings whenever the mouse
      # is over it, regardless of focus, or if there's a widget inside swallowing the event
      # this can't be done in Python because the Event object
      # (that is, the one containing e.widget, e.keysym, e.delta, etc.)
      # goes through subtle transformations when it's received from Tk
      # which is a lossy process
      # so we have to do this Tk side, to keep the text substitutions intact
      # even ignoring that problem, the focus would need to be set
      # to the text widget for event_generate, but
      # then we'd have to restore it back after, which is borderline impossible
      # to do correctly when multiple windows are open
      # this allows us to trigger an event on the text widget even if it doesn't have focus
      # we temporarily disable the focus command via aliasing because
      # the Text widget, unlike most widgets, will take focus when clicked on
      # even if takefocus is False, and we don't want it to randomly steal focus
      # from the widgets it contains just because the window got an event
      if script:
        bind(window, name,
          
          f'''set {W} [{W} %M]
          if {{${W} == ""}} {{ continue }}
          
          interp hide {{}} focus
          interp alias {{}} focus {{}} {focus_cbname}
          catch {{{RE_SCRIPT.sub(repl_W, script)}}} result options
          
          interp alias {{}} focus {{}}
          interp expose {{}} focus
          return -options $options $result
          
          unset {W} result options'''
        )
      
      # set up the bindings that were originally on the window
      # these scripts *will* already have a + prefix
      for script in scripts:
        assert script.startswith(ADD), 'script must be prefixed with %r' % ADD
        
        bind(window, name, script)
    
    def bind_alias(*args):
      # if we are binding a new script to the Text class
      # propagate it to all the windows
      # if we are binding a new script to a window
      # then add the binding, before the Text class binding
      try:
        class_, sequence, script = args
      except ValueError:
        return bind(*args)
      
      class_ = str(class_)
      
      if class_ == CLASS_TEXT:
        # we check for the Text class first to avoid an unnecessary lookup on windows
        # here we need the binding to be applied in advance of calling bind_window
        # which will copy the resulting class binding onto the windows
        result = bind(*args)
        
        # filter out dead windows so bind_window doesn't die on them
        # do not remove dead windows from the list! No touching that here
        # only the window getting destroyed should remove it
        # ideally dead windows should get auto removed from the dictionary
        # because it's a WeakKeyDictionary, but in theory something could
        # still be holding onto its Python reference
        for window_bindings in _windows.items():
          if not window_bindings[0].winfo_exists():
            continue
          
          bind_window(window_bindings, name_sequence(sequence))
        
        return result
      
      # handle the case where you want to put your own binding onto one of these windows
      # we don't need to worry about if this window is dead
      # because bind is supposed to fail with an error if it is anyway
      try:
        window = root_window.nametowidget(class_)
        bindings = _windows[window]
      except KeyError:
        return bind(*args)
      
      name = name_sequence(sequence)
      scripts = bindings.setdefault(name, [])
      
      # if we're not adding this script then clear all previous ones
      if not script.startswith(ADD):
        script = ''.join((ADD, script))
        scripts.clear()
      
      scripts.append(script)
      
      bind_window((window, bindings), name)
      return ''
    
    tk_.call('interp', 'hide', '', 'bind')
    tk_.call('interp', 'alias', '', 'bind', '', root_window.register(bind_alias))
    return (root := (bind, bind_window))
  
  return get

_get_root_embed = _root_embed()


def text_embed(text):
  if text.winfo_class() != CLASS_TEXT:
    raise ValueError('text must have class %r' % CLASS_TEXT)
  
  # setdefault is not used here - it's probably not worth the cost of creating a frame
  if text in _texts:
    raise RuntimeError('text_embed is single shot per-text')
  
  text.bind('<Destroy>', lambda e: _texts.pop(e.widget, None), add=True)
  
  # placeholder to prevent text selection
  frame = ttk.Frame(text)
  _texts[text] = frame
  
  text['state'] = tk.NORMAL
  
  try:
    # we don't use enable_widget here as we don't actually want that
    # (it would disable any child widgets within the text)
    # it should not take focus until an event is fired (it hoards the focus otherwise)
    # it shouldn't have a border, there's a bug where the embedded widgets appear over top of it
    # (put a border around the surrounding frame instead)
    text.configure(takefocus=False, cursor='',
      bg=gui.lookup_style_widget(frame, 'background'), borderwidth=0)
    
    # unbind from Text class so we can't get duplicate events
    # they'll be received from window instead
    # a current weakness of this implementation is that
    # events are not forwarded to individual text widgets, only the Text class
    # which means there isn't any ability to "break" for a particular event
    # aside from putting a bindtag/event on every child, and child's child
    # which of course is the entire thing I'm trying to avoid here
    # programming that feature would be significantly more complicated
    # and for this application, I simply don't need that functionality
    # so basically, embed text will always get Text class events no matter what
    gui.default_bindtags_widget(text, class_=False)
    text.bindtags((BINDTAG,) + text.bindtags())
    
    # delete anything that might've been typed in before the text was passed to us
    # then create the placeholder frame
    text.delete('1.0', tk.END)
    text.window_create(tk.END, window=frame, stretch=True)
  finally:
    text['state'] = tk.DISABLED
  
  window = text.winfo_toplevel()
  
  if window not in _windows:
    window.bind_class(gui.bindtag_window(window),
      '<Destroy>', lambda e: _windows.pop(e.widget, None), add=True)
  
  window_bindings = (window, _windows.setdefault(window, {}))
  
  bind, bind_window = _get_root_embed()
  
  # this step must be done out here
  # if we only got the Text class bindings in get_root_embed
  # then they'd become out of date on future calls
  # this doesn't need to go through name_sequence
  # these are already names
  names = {str(s) for s in bind(CLASS_TEXT)}
  
  # need to ensure the views are bound at least once
  for name in VIEWS:
    bind_window(window_bindings, name)
    names.discard(name)
  
  for name in names:
    bind_window(window_bindings, name)