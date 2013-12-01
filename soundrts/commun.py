import math
import os
import os.path
import re
import string
import sys
import time
import traceback

from constants import *
from lib.log import *
from nofloat import *
from version import *


def encode_msg(msg):
    return "***".join(map(str, msg))

def eval_msg_and_volume(s):
    return [s.split("***")]

MAIN_METASERVER_URL = open("cfg/metaserver.txt").read().strip()

def cos_deg(ad):
    return math.cos(math.radians(ad))

def sin_deg(ad):
    return math.sin(math.radians(ad))

def distance(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return math.sqrt(dx * dx + dy * dy)

def angle(x1, y1, x2, y2, o=0): # retrouve l'angle de l'objet x2,y2 par rapport au joueur x1,y1,o
    d = distance(x1, y1, x2, y2)
    if d == 0:
        return 0 # l'objet est si pres qu'il est toujours face au joueur
    c = (x2 - x1) / d	# s = (y2 - y1) / d
    ac = math.acos(c)
    if y2 - y1 > 0:
        return ac - math.radians(o)
    else:
        return - ac - math.radians(o)

def nombre(n, dire_zero=True, genre="n"):
    n = int(n)
    if (n < 0) or ((n == 0) and (not dire_zero)):
        return []
    if (n == 1) and (genre == "f"):
        return [151] # "une"
    return [1000000 + n]

number = nombre

def letter(c):
    c = string.lower(c)
    if c in string.ascii_lowercase:
        return [string.find(string.ascii_lowercase, c) + 5000]
    else:
        return []

def insert_silences(msg):
    new_msg = []
    for sound in msg:
        new_msg.append(sound)
        new_msg.append(9999) # silence
    return new_msg
