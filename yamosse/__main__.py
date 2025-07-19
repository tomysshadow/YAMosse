import sys
from ast import literal_eval

import yamosse
import yamosse.worker as yamosse_worker


def help_():
  print('Usage: python -m yamosse [-o key value ',
    '-ip import_preset_file_name -ep export_preset_file_name -y output_file_name -rd]')


def main(argc, argv):
  print(yamosse.title(), end='\n\n')
  
  MIN_ARGC = 1
  
  if argc < MIN_ARGC:
    help_()
    return 1
  
  args = argv[MIN_ARGC:]
  argc = len(args)
  
  kwargs = {}
  options_items = {}
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
        a += 1
        kwargs['import_preset_file_name'] = args[a]
      elif arg == '-ep' or arg == '--export-preset':
        a += 1
        kwargs['export_preset_file_name'] = args[a]
      elif arg == '-y' or arg == '--yamscan':
        a += 1
        kwargs['output_file_name'] = args[a]
      elif a < argc3:
        if arg == '-o' or arg == '--options':
          a += 1
          key = args[a]
          
          a += 1
          
          try: options_items[key] = literal_eval(args[a])
          except ValueError:
            help_()
            return 1
  
  if options_items: kwargs['options_items'] = options_items
  
  yamosse_worker.tfhub_cache()
  
  while yamosse.yamosse(**kwargs): pass
  return 0


sys.exit(main(len(sys.argv), sys.argv))