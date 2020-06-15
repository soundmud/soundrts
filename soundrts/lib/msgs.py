from builtins import map
NB_ENCODE_SHIFT = 1000000

def encode_msg(msg):
    return "***".join(map(str, msg))

def eval_msg_and_volume(s):
    return [s.split("***")]

def nb2msg(n):
    n = int(n)
    if n < 0:
        return []
    return [NB_ENCODE_SHIFT + n]
