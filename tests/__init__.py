#!/usr/bin/env python3
import unittest
from os import path, chdir
import sys
import platform
import subprocess


def tests(file, wait=False):
  # a short script to allow performing the tests
  # just by double clicking on this script file to run them
  # it will not interfere with normal discovery, so
  # you can still just use `python -m unittest` on the command line
  # if you prefer
  start_dir = path.dirname(path.realpath(file))
  top_level_dir = path.dirname(start_dir)
  
  # go up a directory from this file
  # so that the code within the imported modules sees
  # the same current directory as it usually expects
  # this is distinct from setting the top level directory
  # which only pertains to module imports
  chdir(top_level_dir)
  
  # do the equivalent of the command line
  # `python -m unittest discover -s YAMosse/tests -t YAMosse`
  result = unittest.TextTestRunner().run(
    unittest.defaultTestLoader.discover(
      start_dir,
      top_level_dir=top_level_dir
    )
  )
  
  # shows "press any key to continue," in order to
  # hold Command Prompt open when running this script from Explorer
  # the exitcode is intentionally not checked, because
  # it'll be an error code if you clicked the X at
  # the top right of the window to close it
  # instead of pressing a key (which is fine)
  if wait:
    subprocess.run(
      'pause' if platform.system() == 'Windows' else 'read',
      shell=True
    )
  
  # no matter where we're called from
  # make sure we exit with an error code
  sys.exit(not result.wasSuccessful())


if __name__ == '__main__': tests(__file__, wait=True)