from soundrts.lib import log
log.add_console_handler()

from soundrts import config
config.mods = ""

from soundrts import version
version.IS_DEV_VERSION = True

import pytest


pytest.main("soundrts/tests")