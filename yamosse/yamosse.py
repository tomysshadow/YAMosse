import os
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Value, Pipe, Event
from threading import Thread, Lock
from sys import exc_info
import traceback
import shlex
import platform
import subprocess
from time import time

import soundfile as sf

import yamosse.root as yamosse_root
import yamosse.options as yamosse_options
import yamosse.worker as yamosse_worker

from .gui import gui
from .gui import progress as gui_progress
from .gui import yamscan as gui_yamscan
from .gui import yamosse as gui_yamosse

NAME = 'YAMosse'
VERSION = '1.0.0'

PROGRESSBAR_MAXIMUM = 100

_title = ' '.join((NAME, VERSION))


def ascii_replace(value):
  return str(value).encode('ascii', 'replace').decode()


def latin1_unescape(value):
  return str(value).encode('latin1').decode('unicode_escape')


def hours_minutes(seconds):
  TO_HMS = 60
  
  m, s = divmod(int(seconds), TO_HMS)
  h, m = divmod(m, TO_HMS)
  
  if h:
    return f'{h:.0f}:{m:02.0f}:{s:02.0f}'
  
  return f'{m:.0f}:{s:02.0f}'


def connection_flush(connection):
  # prevents BrokenPipeError exceptions in workers
  # (they expect that sent messages WILL be delivered, else cause an exception)
  try:
    while True:
      connection.recv()
  except EOFError:
    pass


def batches(seq, size):
  return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def list_ordered(unordered):
  return list('%d. %s' % (index + 1, unordered[index]) for index in range(len(unordered)))


def dict_sorted(d, *args, **kwargs):
  return dict(sorted(d.items(), *args, **kwargs))


def key_getsize(file_name):
  try:
    return os.path.getsize(file_name)
  except OSError:
    pass
  
  return 0


def key_class(item):
  return item[0]


def key_number_of_sounds(item):
  result = 0
  
  # the number of sounds, with uncombined timestamps at the end
  for timestamps in item[1].values():
    result += (len(timestamps) ** 2) - sum(isinstance(ts, int) for ts in timestamps) + 1
  
  return result


def real_relpath(path, start=os.curdir):
  # make path relative if it's within our current directory
  # (just looks nicer in the output)
  real_path = os.path.realpath(path)
  real_start = os.path.realpath(start)
  
  try:
    if os.path.commonpath((real_path, real_start)) != real_start:
      return real_path
  except ValueError:
    return real_path
  
  return os.path.relpath(real_path, start=real_start)


def input_file_names(input_, recursive=True):
  assert input_, 'input must not be empty'
  
  if not isinstance(input_, str):
    if len(input_) > 1: return set(input_)
    input_ = input_[0]
  
  path = real_relpath(input_)
  file_names = set()
  
  # assume path is a directory path, and if it turns out it isn't, then assume it is a file path
  try:
    if recursive:
      # get a flat listing of every file in the directory and its subdirectories
      for walk_root_dir_name, walk_dir_names, walk_file_names in os.walk(path):
        for walk_file_name in walk_file_names:
          file_names.add(os.path.join(walk_root_dir_name, walk_file_name))
      
      # walk does not error if path is not a directory
      if not file_names and not os.path.isdir(path): raise NotADirectoryError
    else:
      # get a flat listing of every file in the directory but not its subdirectories
      with os.scandir(path) as scandir:
        for scandir_entry in scandir:
          if scandir_entry.is_file():
            file_names.add(scandir_entry.path)
  except NotADirectoryError:
    # not a directory, just a regular file
    file_names.add(path)
  
  return file_names


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
     
     
def yamscan_show(widgets, values=None):
  if widgets: return gui_yamscan.show_yamscan(widgets, values=values)
  if values and 'log' in values: print(values['log'])
  return True


def yamscan_files(widgets, options, model_yamnet_class_names):
  # the ideal way to sort the files is from largest to smallest
  # this way, we start processing the largest file right at the start
  # and it hopefully finishes early, leaving only small files to process
  # and allowing us to exit sooner
  # that is, they only take a couple seconds each so we don't spend a lot of time
  # just waiting on one large file to finish in one worker
  # however, if many files were queued, finding the file size for all of them
  # may itself take a while, so we do it in batches and simultaneously submit the work
  BATCH_SIZE = 2 ** 10 # must be a power of two
  BATCH_MASK = BATCH_SIZE - 1
  
  results = {}
  errors = {}
  
  done = {}
  done_lock = Lock()
  
  file_names = list(input_file_names(options.input_, recursive=options.input_recursive))
  file_names_pos = 0
  file_names_len = len(file_names)
    
  next_ = -1
  batch = 0
  
  worker = Value('i', 0)
  shutdown = Event()
  options.initarg(model_yamnet_class_names)
  
  # created immediately before with statement so that these will definitely get closed
  receiver, sender = Pipe(duplex=False)
  
  with receiver, sender:
    process_pool_executor = ProcessPoolExecutor(
      max_workers=options.max_workers,
      initializer=yamosse_worker.initializer,
      initargs=(worker, receiver, sender, shutdown, options,
        model_yamnet_class_names, yamosse_worker.tfhub_enabled())
    )
    
    try:
      # the done dictionary is keyed by future, not file name
      # it doesn't really matter which is the key since we loop through everything
      # but this way, we guarantee there are no duplicate or dropped futures
      # we don't get the future's results here because
      # if an exception occurs, we want it to occur in the YAMScan thread
      def insert_done(future, file_name):
        nonlocal done
        nonlocal done_lock
        
        with done_lock:
          done[future] = file_name
      
      # show any value received by the receiver
      # then show progress and logs for the futures that are done
      def clear_done_normal(received):
        nonlocal done
        nonlocal done_lock
        
        nonlocal file_names_pos
        nonlocal file_names_len
        
        nonlocal next_
        nonlocal batch
        
        if not yamscan_show(widgets, values=received): return False
        
        # just copy it out first so we aren't holding the lock
        # during all the nonsense we have to do below
        with done_lock:
          done_copy = done.copy()
          done.clear()
        
        for future, file_name in done_copy.items():
          try:
            results[file_name] = future.result()
          except sf.LibsndfileError as ex:
            errors[file_name] = ex
          
          log = ''
          
          if next_ == -1:
            batch += 1
            log = 'Batch #%d\n' % batch
          
          file_names_pos += 1
          next_ = file_names_pos & BATCH_MASK
          
          progress = file_names_pos / file_names_len
          log = f'{log}{progress:.4%} complete ({file_names_pos}/{file_names_len}: "{file_name}")'
          
          if not yamscan_show(widgets, {
            'progressbar': progress * PROGRESSBAR_MAXIMUM,
            'log': log
          }): return False
        
        return True
      
      clear_done = None
      
      # if we are in the loading state
      # set the progress bar to normal if the worker has started
      # or if there is a future that is done
      # then change into the normal state so we don't have to continually check this
      def clear_done_loading(received):
        nonlocal done
        nonlocal done_lock
        
        nonlocal clear_done
        
        # we're just reading an int here, not writing it so we don't need to lock this (I think?)
        normal = worker.value
        
        if not normal:
          with done_lock:
            if done: normal = True
        
        if normal:
          if not yamscan_show(widgets, values={
            'progressbar': gui_progress.NORMAL
          }): return False
          
          clear_done = clear_done_normal
          return clear_done_normal(received)
        
        return yamscan_show(widgets, values=received)
      
      clear_done = clear_done_loading
      
      if not yamscan_show(widgets, values={
        'log': 'Created Process Pool Executor\n'
      }): return None
      
      for f in batches(file_names, BATCH_SIZE):
        for file_name in sorted(f, key=key_getsize, reverse=True):
          process_pool_executor.submit(yamosse_worker.worker, file_name).add_done_callback(
            lambda future, file_name=file_name: insert_done(future, file_name))
        
        while next_ and file_names_pos < file_names_len:
          # show any values that we've gotten while waiting for the files to process
          # wait for up to a second so we aren't busy waiting
          # note that this only logs a single message at a time
          # (so that new incoming logs won't have the side effect of keeping the window alive)
          if not clear_done(receiver.recv() if receiver.poll(timeout=1) else None): return None
        
        next_ = -1
    finally:
      # process pool executor must be shut down first
      # so that no exception can prevent it from getting shut down
      # we want to shut it down with wait=False which is not the default
      # so we can't just put it in a with statement
      # sender must be closed before connection flush or else we'll hang indefinitely
      # but we can't just close sender immediately after creating it
      # because it needs to be alive when the workers are submitted, so we close it here instead
      # but it and receiver are still handled by the with block, in case an exception occurs here
      # (that would cause a further BrokenPipeError, but at that point that's expected)
      # connection flush must obviously happen last
      # that just leaves shutdown.set, which can happen before or after sender.close
      # but if we put it after and it causes an exception for some reason
      # that'll just mean sender gets closed twice, redundantly
      # so it goes before sender.close
      process_pool_executor.shutdown(wait=False, cancel_futures=True)
      shutdown.set()
      sender.close()
      connection_flush(receiver)
  
  return results, errors


def yamscan_output(file, results, errors, options, model_yamnet_class_names):
  file_name = ''
  
  item_delimiter = latin1_unescape(options.item_delimiter)
  if not item_delimiter: item_delimiter = ' '
  
  confidence_scores = options.output_confidence_scores
  
  def print_file_name():
    # replace Unicode characters with ASCII when printing
    # to prevent crash when run in Command Prompt
    print(ascii_replace(file_name), end='\n\t', file=file)
  
  # sort from least to most timestamps
  results = dict_sorted(results, key=key_number_of_sounds)
  
  # print results
  for file_name, class_timestamps in results.items():
    print_file_name()
    
    if class_timestamps:
      class_timestamps = dict_sorted(class_timestamps, key=key_class)
      
      for class_, timestamp_scores in class_timestamps.items():
        print(model_yamnet_class_names[class_], end=':\n\t\t', file=file)
        
        for timestamp, score in timestamp_scores.items():
          try:
            hms = ' - '.join(hours_minutes(t) for t in timestamp)
          except TypeError:
            hms = hours_minutes(timestamp)
          
          if confidence_scores:
            hms = f'{hms} ({score:.0%})'
          
          timestamp_scores[timestamp] = hms
        
        print(item_delimiter.join(timestamp_scores.values()), end='\n\t', file=file)
    else:
      print(None, file=file)
    
    print('', file=file)
  
  # print errors
  for file_name, ex in errors.items():
    print_file_name()
    print(ex, file=file)


def yamscan_report_thread_exception(widgets, exc, val, tb):
  return yamscan_show(widgets, values={
    'progressbar': gui_progress.ERROR,
    
    'log': ':\n'.join((
      'Exception in YAMScan thread',
      ''.join(traceback.format_exception(exc, val, tb))
    ))
  })


def yamscan_thread(widgets, output_file_name, options, model_yamnet_class_names):
  try:
    # we open the output file well in advance of actually using it
    # this is because it would suck to do all the work and
    # then fail because the output file is locked or whatever
    with open(output_file_name, mode='w') as output_file:
      seconds = time()
      
      # should be done before calling initarg on the options
      if options.output_options:
        options.print(end='\n\n', file=output_file)
      
      files = yamscan_files(widgets, options, model_yamnet_class_names)
      
      if not files:
        return
      
      results, errors = files
      
      if not yamscan_show(widgets, values={
        'progressbar': gui_progress.DONE,
        'log': 'Finishing, please wait...\n'
      }): return
      
      yamscan_output(output_file, results, errors, options, model_yamnet_class_names)
      
      yamscan_show(widgets, values={
        'log': 'Elapsed Time: %s' % hours_minutes(time() - seconds)
      })
  except:
    yamscan_report_thread_exception(widgets, *exc_info())
  finally:
    yamscan_show(widgets, values={
      'done': 'OK'
    })


def title():
  return _title


def yamosse(**kwargs):
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
  
  window = None
  
  try:
    # try and load the options file first
    options = yamosse_options.Options.load()
  except:
    # if failed to load options file, reset to defaults
    options = yamosse_options.Options()
  
  options_variables = None
  model_yamnet_class_names = yamosse_worker.class_names()
  
  def show_warning(message):
    if window:
      gui.messagebox.showwarning(title=NAME, message=message)
      return
    
    print(message)
  
  def quit_window():
    if window: window.quit()
  
  def yamscan(output_file_name=''):
    nonlocal options
    nonlocal options_variables
    
    TITLE = 'YAMScan'
    
    FILETYPES = (
      ('Text Document', '*.txt'),
      ('All Files', '*.*')
    )
    
    INITIALDIR = 'My YAMScans'
    
    gui.set_variables_to_object(options_variables, options)
    
    options.input_ = shlex.split(options.input_)
    _input = options.input_
    
    if not _input:
      show_warning(gui_yamosse.MESSAGE_INPUT_NONE)
      return
    
    if not options.classes:
      show_warning(gui_yamosse.MESSAGE_CLASSES_NONE)
      return
    
    if output_file_name:
      yamscan_thread(None, output_file_name, options, model_yamnet_class_names)
      return
    
    output_file_name = gui.filedialog.asksaveasfilename(
      parent=window,
      filetypes=FILETYPES,
      initialdir=INITIALDIR,
      initialfile='%s.txt' % os.path.splitext(os.path.basename(_input[0]))[0]
    )
    
    if not output_file_name: return
    
    widgets = gui.gui(
      gui_yamscan.make_yamscan,
      TITLE,
      lambda: open_file(os.path.realpath(output_file_name)),
      progressbar_maximum=PROGRESSBAR_MAXIMUM,
      child=True
    )[1]
    
    # start a thread so the GUI isn't blocked
    Thread(target=yamscan_thread, args=(
      widgets,
      output_file_name,
      options,
      model_yamnet_class_names)
    ).start()
    
  
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
      show_warning(gui_yamosse.MESSAGE_IMPORT_PRESET_VERSION)
      return
    except (KeyError, TypeError):
      show_warning(gui_yamosse.MESSAGE_IMPORT_PRESET_INVALID)
      return
    
    options_variables = gui.get_variables_from_object(options)
    
    quit_window()
  
  def export_preset():
    nonlocal options
    nonlocal options_variables
    
    gui.set_variables_to_object(options_variables, options)
    
    file_name = gui.filedialog.asksaveasfilename(parent=window, filetypes=PRESET_FILETYPES,
      initialdir=PRESET_INITIALDIR, initialfile=PRESET_INITIALFILE)
    
    if not file_name: return
    
    options.export_preset(file_name)
  
  def restore_defaults():
    nonlocal options_variables
    
    if window:
      if not gui.messagebox.askyesno(
        parent=window,
        title=NAME,
        message=gui_yamosse.ASK_RESTORE_DEFAULTS_MESSAGE,
        default=gui.messagebox.NO
      ): return
    
    options_variables = gui.get_variables_from_object(yamosse_options.Options())
    
    quit_window()
  
  if 'restore_defaults' in kwargs:
    if kwargs['restore_defaults']: restore_defaults()
  
  if 'import_preset_file_name' in kwargs:
    import_preset(kwargs['import_preset_file_name'])
  
  if 'options_preset' in kwargs:
    options.preset(kwargs['options_preset'], strict=False)
  
  options.print()
  options_variables = gui.get_variables_from_object(options)
  
  if 'export_preset_file_name' in kwargs:
    export_preset(kwargs['export_preset_file_name'])
  
  if 'output_file_name' in kwargs:
    yamscan(kwargs['output_file_name'])
  
  if kwargs: return None
  
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
  
  window.mainloop()
  
  gui.set_variables_to_object(options_variables, options)
  options.dump()
  return window.children

# "All I need, is for someone to catch my smoke signal, and rescue me, from myself."