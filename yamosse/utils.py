def clamp(number, min_, max_):
  return min(max_, max(number, min_))


def intersects(a, b):
  return any(c in a for c in b)


def ascii_backslashreplace(value):
  return str(value).encode('ascii', 'backslashreplace').decode()


def latin1_unescape(value):
  return str(value).encode('latin1', 'backslashreplace').decode('unicode_escape')


def try_int(value, *args, **kwargs):
  try: return int(value, *args, **kwargs)
  except: return value


def try_split(value, *args, **kwargs):
  try: return value.split(*args, **kwargs)
  except: return value


def hours_minutes(seconds):
  TO_HMS = 60
  
  m, s = divmod(int(seconds), TO_HMS)
  h, m = divmod(m, TO_HMS)
  
  if h:
    return f'{h:.0f}:{m:02.0f}:{s:02.0f}'
  
  return f'{m:.0f}:{s:02.0f}'


def dict_peekitem(d, *args, **kwargs):
  return next(reversed(d.items()), *args, **kwargs)


def dict_sorted(d, *args, **kwargs):
  return dict(sorted(d.items(), *args, **kwargs))


def dict_enumerate(d, *args, **kwargs):
  if isinstance(d, dict): return d
  return dict(enumerate(d, *args, **kwargs))


def dict_once(d, key):
  d_len = len(d)
  return d.setdefault(key, d_len) == d_len


def batched(seq, size):
  return (seq[pos:pos + size] for pos in range(0, len(seq), size))