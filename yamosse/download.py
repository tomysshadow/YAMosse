from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from http.server import BaseHTTPRequestHandler
from shutil import copyfileobj

class DownloadError(URLError): pass


def download(url, path, mode='w+b'):
  # we don't use a with statement here, since we want to return this file out
  file = open(path, mode)
  
  try:
    try:
      with urlopen(url) as response:
        copyfileobj(response, file)
    except HTTPError as ex:
      code = ex.code
      
      raise DownloadError('The server couldn\'t fulfill the request.\nError code: %d\n\n%r' % (
        code, ': '.join(BaseHTTPRequestHandler.responses[code])))
    except URLError as ex:
      raise DownloadError(''.join(('We failed to reach a server.\nReason: ', ex.reason)))
  except:
    file.close()
    raise
  
  return file