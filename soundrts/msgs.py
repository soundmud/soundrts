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

def nb2msg(n, dire_zero=True, genre="n"):
    n = int(n)
    if (n < 0) or ((n == 0) and (not dire_zero)):
        return []
    if (n == 1) and (genre == "f"):
        return [151] # "une"
    return [1000000 + n]
