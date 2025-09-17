"""Get timestamps for sound files by harnessing the power of pristine quality yams."""

import os
import shlex
import platform
from subprocess import Popen
from threading import Event
from functools import cache

import soundfile as sf

import yamosse.progress as yamosse_progress
import yamosse.subsystem as yamosse_subsystem
import yamosse.options as yamosse_options
import yamosse.thread as yamosse_thread
import yamosse.worker as yamosse_worker

try:
  from . import gui
  from .gui import yamosse as gui_yamosse
  from .gui import yamscan as gui_yamscan
except ImportError:
  gui = None

NAME = 'YAMosse'
VERSION = '1.1.0'
TITLE = ' '.join((NAME, VERSION))


class _YAMosse:
  __slots__ = (
    'window', 'subsystem', 'options',
    'model_yamnet_class_names', 'tfhub_enabled'
  )
  
  WEIGHTS_FILETYPES = (
    ('HDF5', '*.h5 *.hdf5'),
    ('All Files', '*.*')
  )
  
  PRESET_FILETYPES = (
    ('JSON', '*.json'),
    ('All Files', '*.*')
  )
  
  PRESET_INITIALDIR = 'My Presets'
  PRESET_INITIALFILE = 'Preset'
  PRESET_DEFAULTEXTENSION = '.json'
  
  MESSAGE_IMPORT_PRESET_VERSION = ('The imported preset is not compatible with this YAMosse '
    'version.')
  
  MESSAGE_IMPORT_PRESET_NOT_JSON = 'The imported preset is not a valid JSON document.'
  MESSAGE_IMPORT_PRESET_INVALID = 'The imported preset is invalid.'
  
  MESSAGE_INPUT_NONE = 'You must select an input folder or files first.'
  MESSAGE_CLASSES_NONE = 'You must select at least one class first.'
  
  MESSAGE_WEIGHTS_NONE = ('You have not specified the weights file. Would you like to download '
    'the standard YAMNet weights file now from Google Cloud Storage? If you answer No, the '
    'YAMScan will be cancelled.')
  
  MESSAGE_ASK_RESTORE_DEFAULTS = 'Are you sure you want to restore the defaults?'
  
  def __init__(self):
    self.window = None
    self.subsystem = None
    
    # try and load the options file first
    # if failed to load options file, reset to defaults
    try:
      self.options = yamosse_options.Options.load()
    except Exception:
      self.options = yamosse_options.Options()
    
    self.model_yamnet_class_names = yamosse_worker.class_names()
    self.tfhub_enabled = yamosse_worker.tfhub_enabled()
  
  def mainloop(self, **kwargs):
    variables = None
    
    if not kwargs:
      if gui:
        variables = gui.get_variables_from_attrs(self.options)
        
        self.window = gui.gui(
          gui_yamosse.make_yamosse,
          
          args=(self, variables, TITLE)
        )[0]
      else:
        kwargs['output_file_name'] = input('Please enter the output file name:\n')
    
    window = self.window
    
    with yamosse_subsystem.subsystem(window, NAME, variables) as subsystem:
      self.subsystem = subsystem
      
      def call(function, *keywords):
        # only call function if all keyword arguments specified
        args = []
        
        for keyword in keywords:
          kwarg = kwargs.get(keyword)
          
          if kwarg is None:
            return None
          
          args.append(kwarg)
        
        return function(*args)
      
      if kwargs:
        call(
          lambda rd: self.restore_defaults() if rd else None,
          'restore_defaults'
        )
        
        call(self.import_preset, 'import_preset_file_name')
        
        call(
          lambda o: self.options.set(o, strict=False),
          'options_attrs'
        )
      
      self.options.print()
      
      if kwargs:
        call(
          lambda r: self.record() if r else None,
          'record'
        )
        
        call(self.export_preset, 'export_preset_file_name')
      
      if window: window.mainloop()
      
      # try and ensure we dump the options
      # even if we crash during a YAMScan
      # we don't do this up above during the operations that manipulate the options
      # in case they would leave it in an invalid state
      # and we don't do it for the window mainloop
      # because that can also change the options and leave it in an invalid state
      try:
        if kwargs:
          call(self.yamscan, 'output_file_name')
          return None
      finally:
        options = self.options
        subsystem.attrs_to_variables(options)
        options.dump()
      
      return window.children
  
  def record(self, start=None, stop=None):
    # this is an optional module
    # so we only import it if we are going to attempt recording
    import yamosse.recording as yamosse_recording
    return yamosse_recording.Recording(self.subsystem, self.options,
      start=start, stop=stop)
  
  def import_preset(self, file_name=''):
    if not file_name:
      window = self.window
      
      assert window, 'file_name must not be empty if there is no window'
      
      file_name = gui.filedialog.askopenfilename(
        parent=window,
        filetypes=self.PRESET_FILETYPES,
        initialdir=self.PRESET_INITIALDIR
      )
      
      if not file_name: return
    
    subsystem = self.subsystem
    
    try:
      self.options = options = yamosse_options.Options.import_preset(file_name)
    except yamosse_options.Options.VersionError:
      subsystem.error(self.MESSAGE_IMPORT_PRESET_VERSION)
    except (yamosse_options.json.JSONDecodeError, UnicodeDecodeError):
      subsystem.error(self.MESSAGE_IMPORT_PRESET_NOT_JSON)
    except (KeyError, TypeError):
      subsystem.error(self.MESSAGE_IMPORT_PRESET_INVALID)
    else:
      subsystem.variables_from_attrs(options)
      subsystem.quit()
  
  def export_preset(self, file_name=''):
    if not file_name:
      window = self.window
      
      assert window, 'file_name must not be empty if there is no window'
      
      file_name = gui.filedialog.asksaveasfilename(
        parent=window,
        filetypes=self.PRESET_FILETYPES,
        initialdir=self.PRESET_INITIALDIR,
        initialfile=self.PRESET_INITIALFILE,
        defaultextension=self.PRESET_DEFAULTEXTENSION
      )
      
      if not file_name: return
    
    options = self.options
    self.subsystem.attrs_to_variables(options)
    options.export_preset(file_name)
  
  def yamscan(self, output_file_name=''):
    FILETYPES = (
      ('Text Document', '*.txt'),
      ('JSON', '*.json'),
      ('All Files', '*.*')
    )
    
    INITIALDIR = 'My YAMScans'
    DEFAULTEXTENSION = '.txt' # must start with period on Linux
    
    subsystem = self.subsystem
    options = self.options
    subsystem.attrs_to_variables(options)
    
    input_ = shlex.split(options.input)
    
    if not input_:
      subsystem.error(self.MESSAGE_INPUT_NONE)
      return
    
    if not options.classes:
      subsystem.error(self.MESSAGE_CLASSES_NONE)
      return
    
    # this event prevents the thread from trying to interact with windows
    # other than the one it was created for
    # because it's possible for a window to get "Indiana Jonesed"
    # and have a new window with the same name as an old one
    # so the thread doesn't see it exit
    exit_ = Event()
    child = None
    
    if not output_file_name:
      window = self.window
      
      assert window, 'output_file_name must not be empty if there is no window'
      
      output_file_name = gui.filedialog.asksaveasfilename(
        parent=window,
        filetypes=FILETYPES,
        initialdir=INITIALDIR,
        initialfile=os.path.splitext(os.path.basename(input_[0]))[0],
        defaultextension=DEFAULTEXTENSION
      )
      
      if not output_file_name: return
      
      child, widgets = gui.gui(
        gui_yamscan.make_yamscan,
        child=True,
        
        args=(
          lambda: self.open_file(os.path.realpath(output_file_name)),
          exit_
        ),
        
        kwargs={
          'progressbar_maximum': yamosse_progress.Progress.MAXIMUM
        }
      )
      
      subsystem.show_callback = gui_yamscan.show_yamscan
      subsystem.widgets = widgets
    
    model_yamnet_class_names = self.model_yamnet_class_names
    tfhub_enabled = self.tfhub_enabled
    
    if not tfhub_enabled and not options.weights:
      if not subsystem.confirm(
        self.MESSAGE_WEIGHTS_NONE,
        default=True,
        parent=child
      ):
        subsystem.show(exit_, values={
          'progressbar': {
            'state': {'args': ((yamosse_progress.State.ERROR.on(),),)},
            'configure': {'kwargs': {'mode': yamosse_progress.Mode.DETERMINATE.value}}
          },
          
          'log': 'The YAMScan was cancelled because there is no weights file.',
          'done': 'OK'
        })
        return
    
    subsystem.start(
      yamosse_thread.thread,
      
      args=(
        output_file_name,
        input_,
        exit_,
        model_yamnet_class_names,
        tfhub_enabled,
        subsystem,
        options
      )
    )
  
  def restore_defaults(self):
    subsystem = self.subsystem
    
    if not subsystem.confirm(
      self.MESSAGE_ASK_RESTORE_DEFAULTS,
      default=False
    ): return
    
    self.options = options = yamosse_options.Options()
    subsystem.variables_from_attrs(options)
    subsystem.quit()
  
  @staticmethod
  @cache
  def input_filetypes():
    available_formats = sf.available_formats()
    
    return (
      [(
        'Supported Files',
        '.'.join(('*', ' *.'.join(available_formats.keys())))
      )]
      
      + [(n, '.'.join(('*', f))) for f, n in available_formats.items()]
      + [('All Files', '*.*')]
    )
  
  @staticmethod
  def open_file(path):
    if os.name == 'nt':
      os.startfile(path)
      return
    
    Popen(('open' if platform.system() == 'Darwin' else 'xdg-open', path))


def yamosse(**kwargs):
  while _YAMosse().mainloop(**kwargs): pass


# "All I need, is for someone to catch my smoke signal, and rescue me, from myself."