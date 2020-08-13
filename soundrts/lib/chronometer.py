import time


def ms(time):
    return int(time * 1000)


_start = {}
_time = {}


def start(key):
    _start[key] = time.time()


def stop(key):
    try:
        _time[key] = time.time() - _start[key]
    except:
        _time[key] = 0


def value(key):
    try:
        return _time[key]
    except:
        return 0


def text(key, label=None):
    if label is None:
        label = key
    try:
        return label + ": % 3i ms" % ms(_time[key])
    except KeyError:
        return label + ": --- ms"
