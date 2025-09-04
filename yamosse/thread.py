import os
from shlex import quote
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Value, Pipe, Event
from threading import Lock
from sys import exc_info
from traceback import format_exception
from contextlib import nullcontext

import soundfile as sf

import yamosse.utils as yamosse_utils
import yamosse.progress as yamosse_progress
import yamosse.worker as yamosse_worker
import yamosse.hiddenfile as yamosse_hiddenfile
import yamosse.download as yamosse_download
import yamosse.output as yamosse_output
import yamosse.identification as yamosse_identification
import yamosse.subsystem as yamosse_subsystem


def _key_getsize(file_name):
  try:
    return os.path.getsize(file_name)
  except OSError:
    return 0


def _file_names_sorted_next(file_names):
  return sorted(next(file_names), key=_key_getsize, reverse=True)


def _connection_flush(connection):
  # prevents BrokenPipeError exceptions in workers
  # (they expect that sent messages WILL be delivered, else cause an exception)
  try:
    while True: connection.recv()
  except EOFError:
    pass


def _real_relpath(path, start=os.curdir):
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


def _input_file_names(input_, recursive=True):
  if not input_:
    raise ValueError('input must not be empty')
  
  if not isinstance(input_, str):
    try:
      input_, = input_
    except ValueError:
      return set(input_)
  
  path = _real_relpath(input_)
  file_names = set()
  
  # assume path is a directory path, and if it turns out it isn't, then assume it is a file path
  try:
    if recursive:
      # get a flat listing of every file in the directory and its subdirectories
      for walk_root_dir_name, walk_dir_names, walk_file_names in os.walk(path):
        for walk_file_name in walk_file_names:
          file_names.add(os.path.join(walk_root_dir_name, walk_file_name))
      
      # walk does not error if path is not a directory
      if not file_names and not os.path.isdir(path):
        raise NotADirectoryError
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


def _download_weights_file_unique(url, path, exit_, subsystem=None, options=None):
  weights = ''
  
  if options:
    weights = options.weights
    
    if weights:
      return open(weights, 'rb')
  
  if subsystem:
    subsystem.show(exit_, values={
      'log': 'Downloading weights file, please wait...'
    })
  
  head, tail = os.path.split(path)
  root, ext = os.path.splitext(tail)
  
  hidden = yamosse_hiddenfile.HiddenFile(
    mode='wb',
    prefix='_'.join((root, '')), suffix=ext, dir=head
  )
  
  yamosse_download.download(url, hidden)
  
  hidden.save = True
  hidden.close()
  
  weights = hidden.name
  assert weights, 'weights must not be empty'
  
  # open the resulting visible file
  file = open(weights, 'rb')
  
  try:
    if subsystem and options:
      subsystem.set_variable_and_attr(options, 'weights', weights)
      options.dump()
  except:
    file.close()
    raise
  
  return file


def _files(input_, exit_,
  model_yamnet_class_names, tfhub_enabled,
  subsystem, options):
  # the ideal way to sort the files is from largest to smallest
  # this way, we start processing the largest file right at the start
  # and it hopefully finishes early, leaving only small files to process
  # and allowing us to exit sooner
  # that is, they only take a couple seconds each so we don't spend a lot of time
  # just waiting on one large file to finish in one worker
  # however, if many files were queued, finding the file size for all of them
  # may itself take a while, so we do it in batches and simultaneously submit the work
  NEXT_SUBMITTING = -1
  NEXT_SUBMITTED = -2
  
  BATCH_SIZE = 2 ** 10 # must be a power of two
  BATCH_MASK = BATCH_SIZE - 1
  
  results = {}
  errors = {}
  
  done = {}
  done_lock = Lock()
  
  file_names = list(_input_file_names(input_, recursive=options.input_recursive))
  file_names_pos = 0
  file_names_len = len(file_names)
  
  next_ = NEXT_SUBMITTING
  batch = 0
  
  number = Value('i', 0)
  step = Value('i', 0)
  steps = file_names_len * yamosse_worker.PROGRESSBAR_MAXIMUM
  
  shutdown = Event()
  
  # created immediately before with statement so that these will definitely get closed
  receiver, sender = Pipe(duplex=False)
  
  with receiver, sender:
    process_pool_executor = ProcessPoolExecutor(
      max_workers=options.max_workers,
      initializer=yamosse_worker.initializer,
      initargs=(number, step, steps, receiver, sender, shutdown, options,
        model_yamnet_class_names, tfhub_enabled)
    )
    
    try:
      def show_received():
        while receiver.poll(): subsystem.show(exit_, values=receiver.recv())
      
      # the done dictionary is keyed by future, not file name
      # it doesn't really matter which is the key since we loop through everything
      # but this way, we guarantee there are no duplicate or dropped futures
      # we don't get the future's results here because
      # if an exception occurs, we want it to occur in the YAMScan thread
      def insert_done(future, file_name):
        with done_lock:
          done[future] = file_name
      
      # show any value received by the receiver
      # then show progress and logs for the futures that are done
      def clear_done_normal():
        nonlocal file_names_pos
        nonlocal file_names_len
        
        nonlocal next_
        nonlocal batch
        
        log = ''
        
        if next_ == NEXT_SUBMITTING:
          next_ = NEXT_SUBMITTED
          batch += 1
          
          log = '\nBatch #%d\n' % batch
        
        # just copy it out first so we aren't holding the lock
        # during all the nonsense we have to do below
        with done_lock:
          done_copy = done.copy()
          done.clear()
        
        for future, file_name in done_copy.items():
          try:
            results[file_name] = future.result()
            status = 'Done'
          except sf.LibsndfileError as ex:
            errors[file_name] = ex
            status = 'Done (with errors)'
          
          file_names_pos += 1
          next_ = file_names_pos & BATCH_MASK
          
          # quote function is used here to match file name format used in output files
          log = f'{log}{status} {file_names_pos}/{file_names_len}: {quote(file_name)}\n'
        
        if log := log.removesuffix('\n'):
          subsystem.show(exit_, values={
            'log': log
          })
        
        show_received()
      
      clear_done = None
      
      # if we are in the loading state
      # set the progress bar to normal if the worker has started
      # or if there is a future that is done
      # then change into the normal state so we don't have to continually check this
      def clear_done_loading():
        nonlocal clear_done
        
        # we're just reading an int here, not writing it so we don't need to lock this (I think?)
        normal = number.value
        
        if not normal:
          with done_lock:
            normal = done
        
        if normal:
          subsystem.show(exit_, values={
            'progressbar': {'configure': {'kwargs': {'mode': yamosse_progress.MODE_DETERMINATE}}}
          })
          
          clear_done = clear_done_normal
          clear_done_normal()
          return
        
        show_received()
      
      clear_done = clear_done_loading
      
      subsystem.show(exit_, values={
        'log': 'Created Process Pool Executor'
      })
      
      file_names_batched = yamosse_utils.batched(file_names, BATCH_SIZE)
      file_names_sorted = _file_names_sorted_next(file_names_batched)
      
      while file_names_batched:
        for file_name in file_names_sorted:
          process_pool_executor.submit(yamosse_worker.worker, file_name).add_done_callback(
            lambda future, file_name=file_name: insert_done(future, file_name))
        
        # while the workers are booting up, sort the next batch
        # this allows both tasks to be done at once
        # although any individual batch should not take longer than a few seconds to sort
        try:
          file_names_sorted = _file_names_sorted_next(file_names_batched)
        except StopIteration:
          file_names_batched = None
        
        while next_ and file_names_pos < file_names_len:
          # waits for incoming values so they'll be instantly shown when they arrive
          # we wait for up to a second so we aren't busy waiting
          # if we didn't get any values, we still want to clear the done futures
          receiver.poll(timeout=1)
          clear_done()
        
        next_ = NEXT_SUBMITTING
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
      _connection_flush(receiver)
  
  return results, errors


def _report_thread_exception(exit_, subsystem, exc, val, tb):
  try:
    subsystem.show(exit_, values={
      'progressbar': {'state': {'args': ((yamosse_progress.STATE_ERROR,),)}},
      
      'log': ':\n'.join((
        'Exception in YAMScan thread',
        ''.join(format_exception(exc, val, tb))
      ))
    })
  except yamosse_subsystem.SubsystemExit: pass


def thread(output_file_name, input_, exit_,
  model_yamnet_class_names, tfhub_enabled,
  subsystem, options):
  try:
    # we open the output file well in advance of actually using it
    # this is because it would suck to do all the work and
    # then fail because the output file is locked or whatever
    # we also hold open the weights file
    # so it can't be deleted in the time between now and the workers using it
    with (
      _download_weights_file_unique(
        yamosse_worker.MODEL_YAMNET_WEIGHTS_URL,
        yamosse_worker.MODEL_YAMNET_WEIGHTS_PATH,
        exit_,
        subsystem=subsystem,
        options=options
      ) if not tfhub_enabled else nullcontext(),
      
      yamosse_output.output(
        output_file_name,
        exit_,
        model_yamnet_class_names,
        
        yamosse_identification.identification(
          option=options.identification
        ),
        
        subsystem=subsystem
      ) as output
    ):
      results, errors = _files(
        input_,
        exit_,
        model_yamnet_class_names,
        tfhub_enabled,
        subsystem,
        options
      )
      
      subsystem.show(exit_, values={
        'progressbar': {yamosse_progress.FUNCTION_DONE: {}},
        'log': 'Finishing, please wait...\n'
      })
      
      output.options(options)
      output.results(results)
      output.errors(errors)
  except yamosse_subsystem.SubsystemExit: pass
  except: _report_thread_exception(exit_, subsystem, *exc_info())
  finally:
    try:
      subsystem.show(exit_, values={
        'done': 'OK'
      })
    except yamosse_subsystem.SubsystemExit: pass