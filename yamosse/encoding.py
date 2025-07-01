def ascii_backslashreplace(value):
  return str(value).encode('ascii', 'backslashreplace').decode()


def latin1_unescape(value):
  return str(value).encode('latin1').decode('unicode_escape')