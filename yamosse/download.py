from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from http.server import BaseHTTPRequestHandler
from shutil import copyfileobj

class DownloadError(IOError): pass


def download(url, file):
  try:
    with urlopen(url) as response:
      copyfileobj(response, file)
  except HTTPError as ex:
    code = ex.code
    
    raise DownloadError("The server couldn't fulfill the request.\nError code: %d\n\n%r" % (code,
      ': '.join(BaseHTTPRequestHandler.responses[code]))) from ex
  except URLError as ex:
    raise DownloadError("We failed to reach a server.\nReason: %s" % ex.reason) from ex