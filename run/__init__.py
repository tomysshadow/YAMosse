from runpy import run_module
import os.path as path

def run(file):
  run_module(path.splitext(path.basename(path.realpath(file)))[0].split('_')[0])