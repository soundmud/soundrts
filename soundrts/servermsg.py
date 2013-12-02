class Sequence(object):

    def __init__(self, sequence):
        self.sequence = [str(x) for x in sequence]

    def send(self, client):
        client.push("sequence %s\n" % " ".join(self.sequence))
