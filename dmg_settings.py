import os.path

# Volume info
application = defines.get("app", "/Users/florianlichteblau/Downloads/soundrts/build/SoundRTS.app")
appname = os.path.basename(application)

# Basic settings
files = [application]
symlinks = {"Applications": "/Applications"}

# Window layout
background = "builtin-arrow"
icon_size = 100
window_rect = ((100, 100), (500, 300))
icon_locations = {
    appname: (125, 150),
    "Applications": (375, 150),
}

format = defines.get("format", "UDZO")
size = defines.get("size", None)
