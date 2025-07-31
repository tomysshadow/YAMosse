import sys

import yamosse
import yamosse.options as yamosse_options
import yamosse.worker as yamosse_worker


def help_():
  print(
    'Usage: python -m yamosse',
    '[-o key value',
    '-ip import_preset_file_name',
    '-ep export_preset_file_name',
    '-y output_file_name',
    '-rd]'
  )


def main(argc, argv):
  print(yamosse.TITLE, end='\n\n')
  
  MIN_ARGC = 1
  
  if argc < MIN_ARGC:
    help_()
    return 1
  
  args = argv[MIN_ARGC:]
  argc = len(args)
  
  kwargs = {}
  options_attrs = {}
  argc2 = argc - 1
  argc3 = argc - 2
  
  for a in range(argc):
    arg = args[a]
    
    if arg == '-h' or arg == '--help':
      help_()
      return 1
    if arg == '-rd' or arg == '--restore_defaults':
      kwargs['restore_defaults'] = True
    if a < argc2:
      if arg == '-ip' or arg == '--import-preset':
        kwargs['import_preset_file_name'] = args[a := a + 1]
      elif arg == '-ep' or arg == '--export-preset':
        kwargs['export_preset_file_name'] = args[a := a + 1]
      elif arg == '-y' or arg == '--yamscan':
        kwargs['output_file_name'] = args[a := a + 1]
      elif a < argc3:
        if arg == '-o' or arg == '--option':
          key = args[a := a + 1]
          
          try: options_attrs[key] = yamosse_options.json.loads(args[a := a + 1])
          except (yamosse_options.json.JSONDecodeError, UnicodeDecodeError):
            help_()
            return 1
  
  if options_attrs: kwargs['options_attrs'] = options_attrs
  
  yamosse_worker.tfhub_cache()
  
  while yamosse.yamosse(**kwargs): pass
  return 0


sys.exit(main(len(sys.argv), sys.argv))