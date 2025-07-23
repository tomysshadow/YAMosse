def ascii_backslashreplace(value):
  return str(value).encode('ascii', 'backslashreplace').decode()


def latin1_unescape(value):
  return str(value).encode('latin1').decode('unicode_escape')


def dict_peekitem(d, *args, **kwargs):
  return next(reversed(d.items()), *args, **kwargs)


def dict_sorted(d, *args, **kwargs):
  return dict(sorted(d.items(), *args, **kwargs))


def dict_enumerate(d):
  if isinstance(d, dict): return d
  return dict(enumerate(d))


def batched(seq, size):
  return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def try_split(value, *args, **kwargs):
  try: return value.split(*args, **kwargs)
  except: return value


def try_int(value):
  try: return int(value)
  except: return value