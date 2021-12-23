from .lib import log
from .paths import SERVER_LOG_PATH

log.clear_handlers()
log.add_rotating_file_handler(SERVER_LOG_PATH, "a", 100000000, 2)
log.add_console_handler()

from . import config

config.load()

from .servermain import main  # noqa
