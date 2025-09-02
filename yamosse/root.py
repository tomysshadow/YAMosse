from os import path

_root_dir = path.dirname(path.realpath(__file__))


def root(dir_=''):
  if path.isabs(dir_):
    return dir_
  
  return path.join(_root_dir, dir_)