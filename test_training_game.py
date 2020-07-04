#! python3
from soundrts import config
from soundrts.mapfile import Map

config.mods = ""

from soundrts import clientmain


if __name__ == "__main__":
    clientmain.init_media()

    # map = "multi/pra2.txt"
    map = "multi/jl5.txt"

    # players = ["test", "easy"], ["random_faction", "random_faction"], ["1", "2"]
    # players = ["test", "aggressive"], ["random_faction", "random_faction"], ["1", "2"]
    players = ["test", "aggressive", "easy"], ["random_faction", "random_faction", "random_faction"], ["1", "1", "2"]

    clientmain.TrainingGame(Map(map), *players).run(speed=20)
