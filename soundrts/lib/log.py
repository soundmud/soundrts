import logging
import logging.handlers
import os
import sys
import urllib


FULL_FORMAT = "%(asctime)s %(levelname)s: %(message)s"
SHORT_FORMAT = "%(levelname)s: %(message)s"

def set_version(version):
    global _VERSION
    _VERSION = version


class HTTPHandler(logging.Handler):

    _done = False

    def __init__(self, url):
        self._url = url
        logging.Handler.__init__(self)

    def emit(self, record):
        if self._done:
            return
        try:
            msg = "exception with %s:\n%s" % (_VERSION, record.exc_text)
            params = urllib.urlencode({"msg": msg})
            urllib.urlopen("%s/logging_errors.php?%s" % (self._url, params)).read()
        except:
            pass
        self._done = True


class SecureFileHandler(logging.FileHandler):
    """
    Avoids an infinite loop creating a huge log file. It happens.
    Useful for a client who resets the log file.
    """
    _nb_records = 0
    _too_many_records = False

    def __init__(self, filename, mode='a', limit=1000000):
        self._records_limit = limit
        logging.FileHandler.__init__(self, filename, mode)

    def emit(self, record):
        if not self._too_many_records:
            self._nb_records += 1
            if self._nb_records <= self._records_limit:
                logging.FileHandler.emit(self, record)
            else:
                self._too_many_records = True
                if self.stream is not None:
                    self.stream.write("*** too many records, logging stopped ***\n")


class _NeverCrash:
    """
    Prevents crash with pythonw.exe (problems with stdout or stderr).
    """
    def __init__(self, f):
        self._f = f

    def __call__(self, *args, **kargs):
        try:
            self._f(*args, **kargs)
        except IOError:
            if "Errno 9" not in str(sys.exc_info()[1]):
                raise


def _configure_handler(h, format, level):
    h.setFormatter(logging.Formatter(format))
    logging.getLogger().addHandler(h)
    h.setLevel(level)

def add_secure_file_handler(name, mode, limit=1000000, level=logging.WARNING, format=FULL_FORMAT):
    h = SecureFileHandler(name, mode, limit)
    _configure_handler(h, format, level)

def add_rotating_file_handler(name, mode, max_size, nb, level=logging.INFO, format=FULL_FORMAT):
    h = logging.handlers.RotatingFileHandler(name, mode, max_size, nb)
    _configure_handler(h, format, level)

def add_http_handler(url, level=logging.ERROR, format=FULL_FORMAT):
    h = HTTPHandler(url)
    _configure_handler(h, format, level)

def add_console_handler(level=logging.INFO, format=SHORT_FORMAT):
    h = logging.StreamHandler(sys.stdout)
    _configure_handler(h, format, level)

debug = _NeverCrash(logging.debug)
info = _NeverCrash(logging.info)
warning = _NeverCrash(logging.warning)
error = _NeverCrash(logging.error)
critical = _NeverCrash(logging.critical)
exception = _NeverCrash(logging.exception)

logging.getLogger().setLevel(logging.DEBUG)


#    def init(self, name, mode, max_size=1000000, http_handler=False):
