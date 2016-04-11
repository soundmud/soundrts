NB_ENCODE_SHIFT = 1000000

def encode_msg(msg):
    return "***".join(map(str, msg))

def eval_msg_and_volume(s):
    return [s.split("***")]

def insert_silences(msg):
    new_msg = []
    for sound in msg:
        new_msg.append(sound)
        new_msg.append(9999) # silence
    return new_msg

def nb2msg(n, say_zero=True, gender="n"):
    n = int(n)
    if (n < 0) or ((n == 0) and (not say_zero)):
        return []
    if (n == 1) and (gender == "f"):
        return [151] # "une"
    return [NB_ENCODE_SHIFT + n]
