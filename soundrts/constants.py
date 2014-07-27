# constants used in more than one module
# Some of them might find a better home later.


MAIN_METASERVER_URL = open("cfg/metaserver.txt").read().strip()

# old value used by some features (stats, ...)
METASERVER_URL = "http://jlpo.free.fr/soundrts/metaserver/"

# simulation
VIRTUAL_TIME_INTERVAL = 300 # milliseconds
COLLISION_RADIUS = 175 # millimeters # 350 / 2
USE_RANGE_MARGIN = 175 # millimeters

# used for packing the orders
NEWLINE_REPLACEMENT = ";"
SPACE_REPLACEMENT = ","

# minimal interval (in seconds) between 2 sounds
ALERT_LIMIT = .5
FOOTSTEP_LIMIT = .1

# don't play events after this limit (in seconds)
EVENT_LIMIT = 3
