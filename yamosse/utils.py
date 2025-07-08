def ascii_backslashreplace(value):
  return str(value).encode('ascii', 'backslashreplace').decode()


def latin1_unescape(value):
  return str(value).encode('latin1').decode('unicode_escape')


def dict_peekitem(d, *args, **kwargs):
  return next(reversed(d.items()), *args, **kwargs)


def dict_sorted(d, *args, **kwargs):
  return dict(sorted(d.items(), *args, **kwargs))


def batched(seq, size):
  return (seq[pos:pos + size] for pos in range(0, len(seq), size))