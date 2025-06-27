import os
import shlex
import platform
import subprocess

import soundfile as sf

import yamosse.subsystem as yamosse_subsystem
import yamosse.options as yamosse_options
import yamosse.thread as yamosse_thread
import yamosse.worker as yamosse_worker

from .gui import gui
from .gui import progress as gui_progress
from .gui import yamscan as gui_yamscan
from .gui import yamosse as gui_yamosse

NAME = 'YAMosse'
VERSION = '1.0.0'

YAMNET_WEIGHTS_PATH = 'yamnet.h5'

WEIGHTS_FILETYPES = (
  ('HDF5', '*.h5'),
  ('All Files', '*.*')
)

PRESET_FILETYPES = (
  ('JSON', '*.json'),
  ('All Files', '*.*')
)

PRESET_INITIALDIR = 'My Presets'
PRESET_INITIALFILE = 'preset.json'

MESSAGE_INPUT_NONE = 'You must select an input folder or files first.'
MESSAGE_CLASSES_NONE = 'You must select at least one class first.'

MESSAGE_WEIGHTS_NONE = ''.join(('You have not specified the weights file. Would you like to ',
  'download the standard YAMNet weights now from Google Cloud Storage? If you click No, the ',
  'YAMScan will be cancelled.'))

MESSAGE_IMPORT_PRESET_VERSION = 'The imported preset is not compatible with this YAMosse version.'
MESSAGE_IMPORT_PRESET_INVALID = 'The imported preset is invalid.'

MESSAGE_ASK_RESTORE_DEFAULTS = 'Are you sure you want to restore the defaults?'

_title = ' '.join((NAME, VERSION))


def open_file(path):
  try:
    os.startfile(path)
  except NotImplementedError:
    subprocess.check_call(('open' if platform.system() == 'Darwin' else 'xdg-open', path))


def sf_input_filetypes():
  available_formats = sf.available_formats()
  input_filetypes = [('Supported Files', '.'.join(('*', ';*.'.join(available_formats.keys()))))]
  
  for format_, name in available_formats.items():
    input_filetypes.append((name, '.'.join(('*', format_))))
  
  input_filetypes.append(('All Files', '*.*'))
  return input_filetypes


def list_ordered(unordered):
  return list('%d. %s' % (index + 1, unordered[index]) for index in range(len(unordered)))


def title():
  return _title


def yamosse(**kwargs):
  window = None
  subsystem = None
  
  try:
    # try and load the options file first
    options = yamosse_options.Options.load()
  except:
    # if failed to load options file, reset to defaults
    options = yamosse_options.Options()
  
  options_variables = None
  model_yamnet_class_names = yamosse_worker.class_names()
  
  def yamscan(output_file_name=''):
    nonlocal options
    nonlocal options_variables
    
    TITLE = 'YAMScan'
    
    FILETYPES = (
      ('Text Document', '*.txt'),
      ('All Files', '*.*')
    )
    
    INITIALDIR = 'My YAMScans'
    
    subsystem.set_variables_to_object(options_variables, options)
    
    input_ = shlex.split(options.input)
    
    if not input_:
      subsystem.show_warning(MESSAGE_INPUT_NONE)
      return
    
    if not options.classes:
      subsystem.show_warning(MESSAGE_CLASSES_NONE)
      return
    
    child = None
    widgets = None
    
    if not output_file_name:
      assert window, 'output_file_name must not be empty if there is no window'
      
      output_file_name = gui.filedialog.asksaveasfilename(
        parent=window,
        filetypes=FILETYPES,
        initialdir=INITIALDIR,
        initialfile='%s.txt' % os.path.splitext(os.path.basename(input_[0]))[0]
      )
      
      if not output_file_name: return
      
      child, widgets = gui.gui(
        gui_yamscan.make_yamscan,
        TITLE,
        lambda: open_file(os.path.realpath(output_file_name)),
        progressbar_maximum=yamosse_thread.PROGRESSBAR_MAXIMUM,
        child=True
      )
      
      subsystem.show_values_callback = gui_yamscan.show_yamscan
      subsystem.widgets = widgets
    
    weights = options.weights
    
    if not weights:
      if not subsystem.ask_yes_no(
        MESSAGE_WEIGHTS_NONE,
        default=False,
        parent=child
      ):
        # TODO: deduplicate this, move to thread, set this asyncronously
        if widgets: yamosse_thread.show(widgets, values={
          'progressbar': gui_progress.ERROR,
          'log': 'The YAMScan was cancelled because there is no weights file.',
          'done': 'OK'
        })
        return
      
      if window:
        options_variables['weights'].set(
          os.path.join(os.path.realpath(os.curdir), YAMNET_WEIGHTS_PATH))
        
        gui.set_variables_to_object(options_variables, options)
      else:
        options.weights = os.path.join(os.path.realpath(os.curdir), YAMNET_WEIGHTS_PATH)
    
    subsystem.start(
      yamosse_thread.thread,
      subsystem,
      output_file_name,
      options,
      input_,
      weights,
      model_yamnet_class_names
    )
    
  
  def import_preset(file_name=''):
    nonlocal options
    nonlocal options_variables
    
    if not file_name:
      assert window, 'file_name must not be empty if there is no window'
      
      file_name = gui.filedialog.askopenfilename(parent=window, filetypes=PRESET_FILETYPES,
        initialdir=PRESET_INITIALDIR)
      
      if not file_name: return
    
    try:
      options = yamosse_options.Options.import_preset(file_name)
    except yamosse_options.Options.VersionError:
      subsystem.show_warning(MESSAGE_IMPORT_PRESET_VERSION)
      return
    except (KeyError, TypeError):
      subsystem.show_warning(MESSAGE_IMPORT_PRESET_INVALID)
      return
    
    options_variables = subsystem.get_variables_from_object(options)
    subsystem.quit()
  
  def export_preset(file_name=''):
    nonlocal options
    nonlocal options_variables
    
    if not file_name:
      assert window, 'file_name must not be empty if there is no window'
      
      gui.set_variables_to_object(options_variables, options)
      
      file_name = gui.filedialog.asksaveasfilename(parent=window, filetypes=PRESET_FILETYPES,
        initialdir=PRESET_INITIALDIR, initialfile=PRESET_INITIALFILE)
      
      if not file_name: return
    
    options.export_preset(file_name)
  
  def restore_defaults():
    nonlocal options_variables
    
    if not subsystem.ask_yes_no(
      MESSAGE_ASK_RESTORE_DEFAULTS,
      default=False
    ):
      return
    
    options_variables = subsystem.get_variables_from_object(yamosse_options.Options())
    subsystem.quit()
  
  if not kwargs:
    options_variables = gui.get_variables_from_object(options)
    
    window = gui.gui(
      gui_yamosse.make_yamosse,
      _title,
      options_variables,
      sf_input_filetypes(),
      list_ordered(model_yamnet_class_names),
      WEIGHTS_FILETYPES,
      yamosse_worker.tfhub_enabled(),
      yamscan,
      import_preset,
      export_preset,
      restore_defaults
    )[0]
  
  subsystem = yamosse_subsystem.subsystem(window, NAME)
  
  if kwargs:
    if 'restore_defaults' in kwargs:
      if kwargs['restore_defaults']: restore_defaults()
    
    if 'import_preset_file_name' in kwargs:
      import_preset(kwargs['import_preset_file_name'])
    
    if 'options_preset' in kwargs:
      options.set(kwargs['options_preset'], strict=False)
  
  options.print()
  
  if kwargs:
    if 'export_preset_file_name' in kwargs:
      export_preset(kwargs['export_preset_file_name'])
    
    if 'output_file_name' in kwargs:
      yamscan(kwargs['output_file_name'])
    
    return None
  
  window.mainloop()
  
  gui.set_variables_to_object(options_variables, options)
  options.dump()
  return window.children

# "All I need, is for someone to catch my smoke signal, and rescue me, from myself."