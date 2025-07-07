import os
import shlex
import platform
import subprocess

import soundfile as sf

import yamosse.progress as yamosse_progress
import yamosse.subsystem as yamosse_subsystem
import yamosse.options as yamosse_options
import yamosse.thread as yamosse_thread
import yamosse.worker as yamosse_worker

try:
  from .gui import gui
  from .gui import yamscan as gui_yamscan
  from .gui import yamosse as gui_yamosse
except ImportError: gui = None

NAME = 'YAMosse'
VERSION = '1.0.0'

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
  'download the standard YAMNet weights file now from Google Cloud Storage? If you click No, the ',
  'YAMScan will be cancelled.'))

MESSAGE_IMPORT_PRESET_VERSION = 'The imported preset is not compatible with this YAMosse version.'
MESSAGE_IMPORT_PRESET_INVALID = 'The imported preset is invalid.'

MESSAGE_ASK_RESTORE_DEFAULTS = 'Are you sure you want to restore the defaults?'

_title = ' '.join((NAME, VERSION))


def open_file(path):
  try: os.startfile(path)
  except NotImplementedError:
    subprocess.check_call(('open' if platform.system() == 'Darwin' else 'xdg-open', path))


def sf_input_filetypes():
  available_formats = sf.available_formats()
  input_filetypes = [('Supported Files', '.'.join(('*', ';*.'.join(available_formats.keys()))))]
  
  for format_, name in available_formats.items():
    input_filetypes.append((name, '.'.join(('*', format_))))
  
  input_filetypes.append(('All Files', '*.*'))
  return input_filetypes


def title():
  return _title


def yamosse(**kwargs):
  window = None
  subsystem = None
  
  # try and load the options file first
  # if failed to load options file, reset to defaults
  try: options = yamosse_options.Options.load()
  except: options = yamosse_options.Options()
  
  model_yamnet_class_names = yamosse_worker.class_names()
  
  def yamscan(output_file_name=''):
    nonlocal options
    
    TITLE = 'YAMScan'
    
    FILETYPES = (
      ('Text Document', '*.txt'),
      ('All Files', '*.*')
    )
    
    INITIALDIR = 'My YAMScans'
    
    subsystem.variables_to_object(options)
    
    input_ = shlex.split(options.input)
    
    if not input_:
      subsystem.show_warning(MESSAGE_INPUT_NONE)
      return
    
    if not options.classes:
      subsystem.show_warning(MESSAGE_CLASSES_NONE)
      return
    
    child = None
    
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
      
      subsystem.show_callback = gui_yamscan.show_yamscan
      subsystem.widgets = widgets
    
    if not options.weights:
      if not subsystem.ask_yes_no(
        MESSAGE_WEIGHTS_NONE,
        default=True,
        parent=child
      ):
        subsystem.show(values={
          'progressbar': yamosse_progress.ERROR,
          'log': 'The YAMScan was cancelled because there is no weights file.',
          'done': 'OK'
        })
        return
    
    subsystem.start(
      yamosse_thread.thread,
      output_file_name,
      input_,
      model_yamnet_class_names,
      subsystem,
      options
    )
  
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
      subsystem.show_warning(MESSAGE_IMPORT_PRESET_VERSION)
      return
    except (KeyError, TypeError):
      subsystem.show_warning(MESSAGE_IMPORT_PRESET_INVALID)
      return
    
    subsystem.variables_from_object(options)
    subsystem.quit()
  
  def export_preset(file_name=''):
    nonlocal options
    
    if not file_name:
      assert window, 'file_name must not be empty if there is no window'
      
      gui.set_variables_to_object(options)
      
      file_name = gui.filedialog.asksaveasfilename(parent=window, filetypes=PRESET_FILETYPES,
        initialdir=PRESET_INITIALDIR, initialfile=PRESET_INITIALFILE)
      
      if not file_name: return
    
    options.export_preset(file_name)
  
  def restore_defaults():
    if not subsystem.ask_yes_no(
      MESSAGE_ASK_RESTORE_DEFAULTS,
      default=False
    ): return
    
    subsystem.variables_from_object(yamosse_options.Options())
    subsystem.quit()
  
  variables = None
  
  if not kwargs:
    if gui:
      variables = gui.get_variables_from_object(options)
      
      window = gui.gui(
        gui_yamosse.make_yamosse,
        _title,
        variables,
        sf_input_filetypes(),
        model_yamnet_class_names,
        WEIGHTS_FILETYPES,
        yamosse_worker.tfhub_enabled(),
        yamscan,
        import_preset,
        export_preset,
        restore_defaults
      )[0]
    else:
      kwargs['output_file_name'] = input('Please enter the output file name:\n')
  
  subsystem = yamosse_subsystem.subsystem(window, NAME, variables)
  
  def call(function, *keywords):
    # only call function if all keyword arguments specified
    args = []
    
    for keyword in keywords:
      kwarg = kwargs.get(keyword)
      if kwarg is None: return None
      
      args.append(kwarg)
    
    return function(*args)
  
  if kwargs:
    call(
      lambda restore_defaults_: restore_defaults() if restore_defaults_ else None,
      'restore_defaults'
    )
    
    call(import_preset, 'import_preset_file_name')
    
    call(
      lambda options_items: options.set(options_items, strict=False),
      'options_items'
    )
  
  options.print()
  
  if kwargs:
    call(export_preset, 'export_preset_file_name')
    call(yamscan, 'output_file_name')
    return None
  
  window.mainloop()
  
  subsystem.variables_to_object(options)
  options.dump()
  return window.children

# "All I need, is for someone to catch my smoke signal, and rescue me, from myself."