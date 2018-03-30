#! python2.7
from soundrts.lib import log
log.add_console_handler()

from soundrts import config
config.mods = ""

from soundrts import version
version.IS_DEV_VERSION = True

import pytest


# note: "--capture=sys" is necessary to run in IDLE
pytest.main("soundrts/tests --capture=sys")
raw_input("[press ENTER to quit]")