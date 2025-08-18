import sys

import yamosse
import yamosse.options as yamosse_options
import yamosse.worker as yamosse_worker
import yamosse.subsystem as yamosse_subsystem


def help_():
  print(
    'Usage: python -m yamosse',
    '[-rd',
    '-r',
    '-ip import_preset_file_name',
    '-ep export_preset_file_name',
    '-y output_file_name',
    '-o key value]'
  )


def main(argc, argv):
  print(yamosse.TITLE, end='\n\n')
  
  MIN_ARGC = 1
  
  if argc < MIN_ARGC:
    help_()
    return 2
  
  args = argv[MIN_ARGC:]
  argc = len(args)
  
  kwargs = {}
  options_attrs = {}
  argc2 = argc - 1
  argc3 = argc - 2
  
  for a in range(argc):
    arg = args[a]
    
    if arg in ('-h', '--help'):
      help_()
      return 2
    elif arg in ('-rd', '--restore_defaults'):
      kwargs['restore_defaults'] = True
    elif arg in ('-r', '--record'):
      kwargs['record'] = True
    elif a < argc2:
      if arg in ('-ip', '--import-preset'):
        kwargs['import_preset_file_name'] = args[a := a + 1]
      elif arg in ('-ep', '--export-preset'):
        kwargs['export_preset_file_name'] = args[a := a + 1]
      elif arg in ('-y', '--yamscan'):
        kwargs['output_file_name'] = args[a := a + 1]
      elif a < argc3:
        if arg in ('-o',  '--option'):
          key = args[a := a + 1]
          
          try: options_attrs[key] = yamosse_options.json.loads(args[a := a + 1])
          except (yamosse_options.json.JSONDecodeError, UnicodeDecodeError):
            help_()
            return 2
  
  if options_attrs: kwargs['options_attrs'] = options_attrs
  
  yamosse_worker.tfhub_cache()
  
  try:
    yamosse.yamosse(**kwargs)
  except yamosse_subsystem.SubsystemError as ex:
    print(ex)
    return 1
  
  return 0


sys.exit(main(len(sys.argv), sys.argv))