import os
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Value, Pipe, Event
from threading import Lock
from sys import exc_info
import traceback

import soundfile as sf

import yamosse.utils as yamosse_utils
import yamosse.progress as yamosse_progress
import yamosse.worker as yamosse_worker
import yamosse.download as yamosse_download
import yamosse.output as yamosse_output
import yamosse.subsystem as yamosse_subsystem

PROGRESSBAR_MAXIMUM = 100


def key_getsize(file_name):
  try: return os.path.getsize(file_name)
  except OSError: return 0


def file_names_sorted_next(file_names):
  return sorted(next(file_names), key=key_getsize, reverse=True)


def connection_flush(connection):
  # prevents BrokenPipeError exceptions in workers
  # (they expect that sent messages WILL be delivered, else cause an exception)
  try:
    while True: connection.recv()
  except EOFError: pass


def real_relpath(path, start=os.curdir):
  # make path relative if it's within our current directory
  # (just looks nicer in the output)
  real_path = os.path.realpath(path)
  real_start = os.path.realpath(start)
  
  try:
    if os.path.commonpath((real_path, real_start)) != real_start:
      return real_path
  except ValueError: return real_path
  
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


def download_weights_file_unique(url, path, min_=1, max_=1000, subsystem=None, options=None):
  if options:
    weights = options.weights
    if weights: return open(weights, 'rb')
  
  if subsystem:
    subsystem.show(values={
      'log': 'Downloading weights file, please wait...'
    })
  
  path = os.path.join(os.path.realpath(os.curdir), path)
  
  def increment_file_name():
    root, ext = os.path.splitext(path)
    
    return (path if num == min_ else '%s (%d)%s' % (root, num, ext
      ) for num in range(min_, max_))
  
  for i in increment_file_name():
    try: file = yamosse_download.download(url, i, mode='xb')
    except FileExistsError: continue
    
    try:
      assert i, 'i must not be empty'
      
      if options:
        options.weights = i
        options.dump()
      
      if subsystem: subsystem.set_variable_after_idle('weights', i)
      return file
    except:
      file.close()
      raise
  
  raise IOError('The weights file %r could not be created uniquely.' % path)


def files(input_, model_yamnet_class_names, subsystem, options):
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
  
  options.initarg(input_, model_yamnet_class_names)
  
  results = {}
  errors = {}
  
  done = {}
  done_lock = Lock()
  
  file_names = list(input_file_names(options.input, recursive=options.input_recursive))
  file_names_pos = 0
  file_names_len = len(file_names)
    
  next_ = -1
  batch = 0
  
  worker = Value('i', 0)
  shutdown = Event()
  
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
        
        subsystem.show(values=received)
        
        # just copy it out first so we aren't holding the lock
        # during all the nonsense we have to do below
        with done_lock:
          done_copy = done.copy()
          done.clear()
        
        for future, file_name in done_copy.items():
          try: results[file_name] = future.result()
          except sf.LibsndfileError as ex: errors[file_name] = ex
          
          log = ''
          
          if next_ == -1:
            batch += 1
            log = '\nBatch #%d\n' % batch
          
          file_names_pos += 1
          next_ = file_names_pos & BATCH_MASK
          
          progress = file_names_pos / file_names_len
          log = f'{log}{progress:.4%} complete ({file_names_pos}/{file_names_len}: "{file_name}")'
          
          subsystem.show(values={
            'progressbar': progress * PROGRESSBAR_MAXIMUM,
            'log': log
          })
      
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
          subsystem.show(values={
            'progressbar': yamosse_progress.NORMAL
          })
          
          clear_done = clear_done_normal
          clear_done_normal(received)
          return
        
        subsystem.show(values=received)
      
      clear_done = clear_done_loading
      
      subsystem.show(values={
        'log': 'Created Process Pool Executor'
      })
      
      file_names_batched = yamosse_utils.batched(file_names, BATCH_SIZE)
      file_names_sorted = file_names_sorted_next(file_names_batched)
      
      while file_names_batched:
        for file_name in file_names_sorted:
          process_pool_executor.submit(yamosse_worker.worker, file_name).add_done_callback(
            lambda future, file_name=file_name: insert_done(future, file_name))
        
        # while the workers are booting up, sort the next batch
        # this allows both tasks to be done at once
        # although any individual batch should not take longer than a few seconds to sort
        try: file_names_sorted = file_names_sorted_next(file_names_batched)
        except StopIteration: file_names_batched = None
        
        while next_ and file_names_pos < file_names_len:
          # show any values that we've gotten while waiting for the files to process
          # wait for up to a second so we aren't busy waiting
          # note that this only logs a single message at a time
          # (so that new incoming logs won't have the side effect of keeping the window alive)
          clear_done(receiver.recv() if receiver.poll(timeout=1) else None)
        
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


def report_thread_exception(subsystem, exc, val, tb):
  try:
    subsystem.show(values={
      'progressbar': yamosse_progress.ERROR,
      
      'log': ':\n'.join((
        'Exception in YAMScan thread',
        ''.join(traceback.format_exception(exc, val, tb))
      ))
    })
  except yamosse_subsystem.SubsystemExit: pass


def thread(output_file_name, input_, model_yamnet_class_names, subsystem, options):
  try:
    # we open the output file well in advance of actually using it
    # this is because it would suck to do all the work and
    # then fail because the output file is locked or whatever
    # we also hold open the weights file
    # so it can't be deleted in the time between now and the workers using it
    with (
      download_weights_file_unique(
        yamosse_worker.MODEL_YAMNET_WEIGHTS_URL,
        yamosse_worker.MODEL_YAMNET_WEIGHTS_PATH,
        subsystem=subsystem,
        options=options
      ) as weights_file,
      
      yamosse_output.output(
        output_file_name,
        model_yamnet_class_names,
        subsystem=subsystem
      ) as output
    ):
      # should be done before calling initarg on the options
      output.options(options)
      
      results, errors = files(input_, model_yamnet_class_names, subsystem, options)
      
      subsystem.show(values={
        'progressbar': yamosse_progress.DONE,
        'log': 'Finishing, please wait...\n'
      })
      
      output.results(results)
      output.errors(errors)
  except yamosse_subsystem.SubsystemExit: pass
  except: report_thread_exception(subsystem, *exc_info())
  finally:
    try:
      subsystem.show(values={
        'done': 'OK'
      })
    except yamosse_subsystem.SubsystemExit: pass