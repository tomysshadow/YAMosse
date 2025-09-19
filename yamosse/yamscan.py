import os
from shlex import quote
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import threading
from sys import exc_info
from traceback import format_exception
from contextlib import suppress, nullcontext

import soundfile as sf

import yamosse.utils as yamosse_utils
import yamosse.progress as yamosse_progress
import yamosse.worker as yamosse_worker
import yamosse.hiddenfile as yamosse_hiddenfile
import yamosse.download as yamosse_download
import yamosse.output as yamosse_output
import yamosse.identification as yamosse_identification
import yamosse.subsystem as yamosse_subsystem


class _Done:
  __slots__ = (
    '_d', '_lock',
    'yamscan', 'results', 'errors',
    'subsystem', 'exit_',
    'next_', 'batch',
    'clear',
    '_file_names_batched'
  )
  
  NEXT_SUBMITTING = -1
  NEXT_SUBMITTED = -2
  
  BATCH_SIZE = 2 ** 10 # must be a power of two
  BATCH_MASK = BATCH_SIZE - 1
  
  def __init__(self, yamscan, results, errors, subsystem, exit_):
    self._d = {}
    self._lock = threading.Lock()
    
    self.yamscan = yamscan
    self.results = results
    self.errors = errors
    
    self.subsystem = subsystem
    self.exit_ = exit_
    
    self.next_ = self.NEXT_SUBMITTING
    self.batch = 0
    
    self.clear = self._clear_loading
    
    self._file_names_batched = yamosse_utils.batched(
      yamscan.file_names,
      self.BATCH_SIZE
    )
  
  def next_batch(self):
    try:
      return sorted(next(self._file_names_batched),
        key=self._key_getsize, reverse=True)
    except StopIteration:
      return None
  
  # the done dictionary is keyed by future, not file name
  # it doesn't really matter which is the key since we loop through everything
  # but this way, we guarantee there are no duplicate or dropped futures
  # we don't get the future's results here because
  # if an exception occurs, we want it to occur in the YAMScan thread
  def insert(self, future, file_name):
    with self._lock:
      self._d[future] = file_name
  
  # if we are in the loading state
  # set the progress bar to normal if the worker has started
  # or if there is a future that is done
  # then change into the normal state so we don't have to continually check this
  def _clear_loading(self):
    yamscan = self.yamscan
    subsystem = self.subsystem
    exit_ = self.exit_
    
    # we're just reading an int here, not writing it so we don't need to lock this (I think?)
    normal = yamscan.number.value
    
    if not normal:
      with self._lock:
        normal = self._d
    
    if normal:
      subsystem.show(exit_, values={
        'progressbar': {
          'configure': {'kwargs': {'mode': yamosse_progress.Mode.DETERMINATE.value}}
        }
      })
      
      self.clear = clear = self._clear_normal
      clear()
      return
    
    yamscan.show_received(subsystem, exit_)
  
  # show any value received by the receiver
  # then show progress and logs for the futures that are done
  def _clear_normal(self):
    log = ''
    
    if self.next_ == self.NEXT_SUBMITTING:
      self.next_ = self.NEXT_SUBMITTED
      self.batch += 1
      
      log = '\nBatch #%d\n' % self.batch
    
    yamscan = self.yamscan
    
    # just copy it out first so we aren't holding the lock
    # during all the nonsense we have to do below
    with self._lock:
      d = self._d
      d_copy = d.copy()
      d.clear()
    
    for future, file_name in d_copy.items():
      try:
        self.results[file_name] = future.result()
        status = 'Done'
      except sf.LibsndfileError as exc:
        self.errors[file_name] = exc
        status = 'Done (with errors)'
      
      yamscan.file_names_pos += 1
      
      file_names_pos = yamscan.file_names_pos
      file_names_len = yamscan.file_names_len
      
      self.next_ = file_names_pos & self.BATCH_MASK
      
      # quote function is used here to match file name format used in output files
      log = f'{log}{status} {file_names_pos}/{file_names_len}: {quote(file_name)}\n'
    
    subsystem = self.subsystem
    exit_ = self.exit_
    
    if log := log.removesuffix('\n'):
      subsystem.show(exit_, values={
        'log': log
      })
    
    yamscan.show_received(subsystem, exit_, force=log)
  
  @staticmethod
  def _key_getsize(file_name):
    try:
      return os.path.getsize(file_name)
    except OSError:
      return 0


class YAMScan:
  __slots__ = (
    'file_names', 'file_names_pos', 'file_names_len',
    'model_yamnet_class_names', 'tfhub_enabled',
    'number', 'progress', 'receiver', 'sender', 'shutdown', 'options'
  )
  
  def __init__(self, output_file_name, input_,
    model_yamnet_class_names, tfhub_enabled,
    subsystem, options, exit_=None):
    self.file_names = file_names = list(
      self._input_file_names(
        input_,
        recursive=options.input_recursive
      )
    )
    
    self.file_names_pos = 0
    self.file_names_len = len(file_names)
    
    self.model_yamnet_class_names = model_yamnet_class_names
    self.tfhub_enabled = tfhub_enabled
    
    self.number = multiprocessing.Value('i', 0)
    self.progress = None
    self.receiver = None
    self.sender = None
    self.shutdown = multiprocessing.Event()
    self.options = options
    
    subsystem.start(
      self._thread,
      
      args=(
        output_file_name,
        subsystem,
        threading.Event() if exit_ is None else exit_
      )
    )
  
  def show_received(self, subsystem, exit_, force=True):
    receiver = self.receiver
    
    shown = receiver.poll()
    
    if not shown and force:
      subsystem.show(exit_)
      return
    
    while shown:
      subsystem.show(exit_, values=receiver.recv())
      shown = receiver.poll()
  
  def flush_received(self):
    # prevents BrokenPipeError exceptions in workers
    # (they expect that sent messages WILL be delivered, else cause an exception)
    receiver = self.receiver
    
    with suppress(EOFError):
      while True:
        receiver.recv()
  
  def _thread(self, output_file_name, subsystem, exit_):
    try:
      options = self.options
      
      # we open the output file well in advance of actually using it
      # this is because it would suck to do all the work and
      # then fail because the output file is locked or whatever
      # we also hold open the weights file
      # so it can't be deleted in the time between now and the workers using it
      with (
        self._download_weights_file_unique(
          yamosse_worker.MODEL_YAMNET_WEIGHTS_URL,
          yamosse_worker.MODEL_YAMNET_WEIGHTS_PATH,
          exit_,
          subsystem=subsystem,
          options=options
        ) if not self.tfhub_enabled else nullcontext(),
        
        yamosse_output.output(
          output_file_name,
          exit_,
          self.model_yamnet_class_names,
          
          yamosse_identification.identification(
            option=options.identification
          ),
          
          subsystem=subsystem
        ) as output
      ):
        results, errors = self._files(subsystem, exit_)
        
        subsystem.show(exit_, values={
          'progressbar': {
            'done': {}
          },
          
          'log': 'Finishing, please wait...\n'
        })
        
        output.options(options)
        output.results(results)
        output.errors(errors)
    except yamosse_subsystem.SubsystemExit: pass
    except: self._report_thread_exception(subsystem, exit_, *exc_info())
    finally:
      try:
        subsystem.show(exit_, values={
          'done': 'OK'
        })
      except yamosse_subsystem.SubsystemExit: pass
  
  def _files(self, subsystem, exit_):
    # the ideal way to sort the files is from largest to smallest
    # this way, we start processing the largest file right at the start
    # and it hopefully finishes early, leaving only small files to process
    # and allowing us to exit sooner
    # that is, they only take a couple seconds each so we don't spend
    # a lot of time just waiting on one large file to finish in one worker
    # however, if many files were queued, finding the file size for all of them
    # may itself take a while, so we do it in batches
    # and simultaneously submit the work
    results = {}
    errors = {}
    
    shutdown = self.shutdown
    receiver, sender = multiprocessing.Pipe(duplex=False)
    
    # this is done immediately after opening the pipe to ensure it closes
    with (receiver, sender):
      self.progress = yamosse_progress.Progress(
        multiprocessing.Value('i', 0),
        self.file_names_len,
        sender
      )
      
      self.receiver = receiver
      self.sender = sender
      
      process_pool_executor = ProcessPoolExecutor(
        max_workers=self.options.max_workers,
        initializer=yamosse_worker.initializer,
        initargs=(self,)
      )
      
      try:
        subsystem.show(exit_, values={
          'log': 'Created Process Pool Executor'
        })
        
        done = _Done(self, results, errors, subsystem, exit_)
        next_batch = done.next_batch()
        
        while next_batch:
          for file_name in next_batch:
            process_pool_executor.submit(
              yamosse_worker.worker,
              file_name
            ).add_done_callback(
              lambda future, file_name=file_name: done.insert(future, file_name)
            )
          
          # while the workers are booting up, sort the next batch
          # this allows both tasks to be done at once
          # although any individual batch should not take longer
          # than a few seconds to sort
          next_batch = done.next_batch()
          
          while done.next_ and self.file_names_pos < self.file_names_len:
            # waits for incoming values so they'll be instantly shown when they arrive
            # we wait for up to a second so we aren't busy waiting
            # if we didn't get any values, we still want to clear the done futures
            receiver.poll(timeout=1)
            done.clear()
          
          done.next_ = done.NEXT_SUBMITTING
      finally:
        # process pool executor must be shut down first
        # so that no exception can prevent it from getting shut down
        # we want to shut it down with wait=False which is not the default
        # so we can't just put it in a with statement
        # sender must be closed before connection flush or else we'll hang indefinitely
        # but we can't just close sender immediately after creating it
        # because it needs to be alive when the workers are submitted
        # so we close it here instead
        # but it and receiver are still handled by the with block
        # in case an exception occurs here
        # (that would cause a further BrokenPipeError, but at that point that's expected)
        # connection flush must obviously happen last
        # that just leaves shutdown.set, which can happen before or after sender.close
        # but if we put it after and it causes an exception for some reason
        # that'll just mean sender gets closed twice, redundantly
        # so it goes before sender.close
        process_pool_executor.shutdown(wait=False, cancel_futures=True)
        shutdown.set()
        sender.close()
        self.flush_received()
      
      return results, errors
  
  @staticmethod
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
  
  @classmethod
  def _input_file_names(cls, input_, recursive=True):
    if not input_:
      raise ValueError('input must not be empty')
    
    if not isinstance(input_, str):
      try:
        input_, = input_
      except ValueError:
        return set(input_)
    
    path = cls._real_relpath(input_)
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
  
  @staticmethod
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
  
  @staticmethod
  def _report_thread_exception(subsystem, exit_, exc, val, tb):
    try:
      subsystem.show(exit_, values={
        'progressbar': {
          'state': {'args': ((yamosse_progress.State.ERROR.on(),),)},
          'configure': {'kwargs': {'mode': yamosse_progress.Mode.DETERMINATE.value}}
        },
        
        'log': ':\n'.join((
          'Exception in YAMScan thread',
          ''.join(format_exception(exc, val, tb))
        ))
      })
    except yamosse_subsystem.SubsystemExit: pass