from os import path

def root(dir_):
  if path.isabs(dir_):
    return dir_
  
  return path.join(path.dirname(path.realpath(__file__)), dir_)