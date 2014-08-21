import os

from campaign import Campaign
import config
from package import get_all_packages_paths


def _get_campaigns():
    w = []
    for mp in get_all_packages_paths():
        d = os.path.join(mp, "single")
        if os.path.isdir(d):
            for n in os.listdir(d):
                p = os.path.join(d, n)
                if os.path.isdir(p):
                    if n == "campaign":
                        w.append(Campaign(p, [4267]))
                    else:
                        w.append(Campaign(p))
    return w

_campaigns = None
_mods = None

def campaigns():
    global _campaigns, _mods
    if _campaigns is None or _mods != config.mods:
        _campaigns = _get_campaigns()
    return _campaigns
