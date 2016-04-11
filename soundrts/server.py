from lib import log
from paths import SERVER_LOG_PATH
log.add_rotating_file_handler(SERVER_LOG_PATH, "a", 100000000, 2)
log.add_console_handler()

from servermain import main