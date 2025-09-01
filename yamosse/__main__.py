import sys
import argparse

import yamosse
import yamosse.options as yamosse_options
import yamosse.worker as yamosse_worker
import yamosse.subsystem as yamosse_subsystem


def main():
  print(yamosse.TITLE, end='\n\n')
  
  parser = argparse.ArgumentParser(
    prog=yamosse.__name__,
    description=yamosse.__doc__
  )
  
  parser.add_argument('-rd', '--restore_defaults',
    action='store_true', default=argparse.SUPPRESS)
  
  parser.add_argument('-r', '--record',
    action='store_true', default=argparse.SUPPRESS)
  
  parser.add_argument('-ip', '--import-preset',
    dest='import_preset_file_name', default=argparse.SUPPRESS)
  
  parser.add_argument('-ep', '--export-preset',
    dest='export_preset_file_name', default=argparse.SUPPRESS)
  
  parser.add_argument('-y', '--yamscan',
    dest='output_file_name', default=argparse.SUPPRESS)
  
  parser.add_argument('-o', '--option', nargs=2,
    action='append', dest='options_attrs', metavar=('KEY', 'VALUE'), default=[])
  
  args = parser.parse_args()
  options_attrs = dict(args.options_attrs)
  
  for key, value in options_attrs.items():
    try:
      options_attrs[key] = yamosse_options.json.loads(value)
    except (yamosse_options.json.JSONDecodeError, UnicodeDecodeError) as ex:
      parser.error(str(ex))
  
  if options_attrs:
    args.options_attrs = options_attrs
  else:
    del args.options_attrs
  
  yamosse_worker.tfhub_cache()
  
  try:
    yamosse.yamosse(**vars(args))
  except yamosse_subsystem.SubsystemError as ex:
    print(ex)
    return 1
  
  return 0


sys.exit(main())