def ascii_replace(value):
  return str(value).encode('ascii', 'replace').decode()


def latin1_unescape(value):
  return str(value).encode('latin1').decode('unicode_escape')