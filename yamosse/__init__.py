"""Get timestamps for sound files by harnessing the power of pristine quality yams."""

import os
import shlex
import platform
from subprocess import Popen
from threading import Event

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

MESSAGE_IMPORT_PRESET_VERSION = 'The imported preset is not compatible with this YAMosse version.'
MESSAGE_IMPORT_PRESET_NOT_JSON = 'The imported preset is not a valid JSON document.'
MESSAGE_IMPORT_PRESET_INVALID = 'The imported preset is invalid.'

MESSAGE_INPUT_NONE = 'You must select an input folder or files first.'
MESSAGE_CLASSES_NONE = 'You must select at least one class first.'

MESSAGE_WEIGHTS_NONE = ('You have not specified the weights file. Would you like to download the '
  'standard YAMNet weights file now from Google Cloud Storage? If you answer No, the YAMScan will '
  'be cancelled.')

MESSAGE_ASK_RESTORE_DEFAULTS = 'Are you sure you want to restore the defaults?'


def open_file(path):
  if os.name == 'nt':
    os.startfile(path)
    return
  
  Popen(('open' if platform.system() == 'Darwin' else 'xdg-open', path))


def sf_input_filetypes():
  available_formats = sf.available_formats()
  
  return (
    [(
      'Supported Files',
      '.'.join(('*', ' *.'.join(available_formats.keys())))
    )]
    
    + [(n, '.'.join(('*', f))) for f, n in available_formats.items()]
    + [('All Files', '*.*')]
  )


def _mainloop(**kwargs):
  window = None
  subsystem = None
  
  # try and load the options file first
  # if failed to load options file, reset to defaults
  try:
    options = yamosse_options.Options.load()
  except Exception:
    options = yamosse_options.Options()
  
  model_yamnet_class_names = yamosse_worker.class_names()
  tfhub_enabled = yamosse_worker.tfhub_enabled()
  
  def record(start=None, stop=None):
    # this is an optional module
    # so we only import it if we are going to attempt recording
    import yamosse.recording as yamosse_recording
    return yamosse_recording.Recording(subsystem, options,
      start=start, stop=stop)
  
  def import_preset(file_name=''):
    nonlocal options
    
    if not file_name:
      assert window, 'file_name must not be empty if there is no window'
      
      file_name = gui.filedialog.askopenfilename(parent=window, filetypes=PRESET_FILETYPES,
        initialdir=PRESET_INITIALDIR)
      
      if not file_name: return
    
    try:
      options = yamosse_options.Options.import_preset(file_name)
    except yamosse_options.Options.VersionError:
      subsystem.error(MESSAGE_IMPORT_PRESET_VERSION)
    except (yamosse_options.json.JSONDecodeError, UnicodeDecodeError):
      subsystem.error(MESSAGE_IMPORT_PRESET_NOT_JSON)
    except (KeyError, TypeError):
      subsystem.error(MESSAGE_IMPORT_PRESET_INVALID)
    else:
      subsystem.variables_from_attrs(options)
      subsystem.quit()
  
  def export_preset(file_name=''):
    if not file_name:
      assert window, 'file_name must not be empty if there is no window'
      
      file_name = gui.filedialog.asksaveasfilename(
        parent=window,
        filetypes=PRESET_FILETYPES,
        initialdir=PRESET_INITIALDIR,
        initialfile=PRESET_INITIALFILE,
        defaultextension=PRESET_DEFAULTEXTENSION
      )
      
      if not file_name: return
    
    subsystem.attrs_to_variables(options)
    options.export_preset(file_name)
  
  def yamscan(output_file_name=''):
    FILETYPES = (
      ('Text Document', '*.txt'),
      ('JSON', '*.json'),
      ('All Files', '*.*')
    )
    
    INITIALDIR = 'My YAMScans'
    DEFAULTEXTENSION = '.txt' # must start with period on Linux
    
    subsystem.attrs_to_variables(options)
    
    input_ = shlex.split(options.input)
    
    if not input_:
      subsystem.error(MESSAGE_INPUT_NONE)
      return
    
    if not options.classes:
      subsystem.error(MESSAGE_CLASSES_NONE)
      return
    
    # this event prevents the thread from trying to interact with windows
    # other than the one it was created for
    # because it's possible for a window to get "Indiana Jonesed"
    # and have a new window with the same name as an old one
    # so the thread doesn't see it exit
    exit_ = Event()
    child = None
    
    if not output_file_name:
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
          lambda: open_file(os.path.realpath(output_file_name)),
          exit_
        ),
        
        kwargs={
          'progressbar_maximum': yamosse_worker.PROGRESSBAR_MAXIMUM
        }
      )
      
      subsystem.show_callback = gui_yamscan.show_yamscan
      subsystem.widgets = widgets
    
    if not tfhub_enabled and not options.weights:
      if not subsystem.confirm(
        MESSAGE_WEIGHTS_NONE,
        default=True,
        parent=child
      ):
        subsystem.show(exit_, values={
          'progressbar': {
            'state': {'args': ((yamosse_progress.State.ERROR,),)},
            'configure': {'kwargs': {'mode': yamosse_progress.Mode.DETERMINATE}}
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
  
  def restore_defaults():
    nonlocal options
    
    if not subsystem.confirm(
      MESSAGE_ASK_RESTORE_DEFAULTS,
      default=False
    ): return
    
    options = yamosse_options.Options()
    subsystem.variables_from_attrs(options)
    subsystem.quit()
  
  variables = None
  
  if not kwargs:
    if gui:
      variables = gui.get_variables_from_attrs(options)
      
      window = gui.gui(
        gui_yamosse.make_yamosse,
        
        args=(
          TITLE,
          variables,
          sf_input_filetypes(),
          record,
          model_yamnet_class_names,
          WEIGHTS_FILETYPES,
          tfhub_enabled,
          import_preset,
          export_preset,
          yamscan,
          restore_defaults
        )
      )[0]
    else:
      kwargs['output_file_name'] = input('Please enter the output file name:\n')
  
  subsystem = yamosse_subsystem.subsystem(window, NAME, variables)
  
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
      lambda restore_defaults_: restore_defaults() if restore_defaults_ else None,
      'restore_defaults'
    )
    
    call(import_preset, 'import_preset_file_name')
    
    call(
      lambda options_attrs: options.set(options_attrs, strict=False),
      'options_attrs'
    )
  
  options.print()
  
  if kwargs:
    call(
      lambda record_: record() if record_ else None,
      'record'
    )
    
    call(export_preset, 'export_preset_file_name')
  
  if window: window.mainloop()
  
  # try and ensure we dump the options
  # even if we crash during a YAMScan
  # we don't do this up above during the operations that manipulate the options
  # in case they would leave it in an invalid state
  # and we don't do it for the window mainloop
  # because that can also change the options and leave it in an invalid state
  try:
    if kwargs:
      call(yamscan, 'output_file_name')
      return None
  finally:
    subsystem.attrs_to_variables(options)
    options.dump()
  
  return window.children


def yamosse(**kwargs):
  while _mainloop(**kwargs): pass


# "All I need, is for someone to catch my smoke signal, and rescue me, from myself."