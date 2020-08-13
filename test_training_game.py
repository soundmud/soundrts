#! .venv\Scripts\python.exe
import traceback

from soundrts import config

config.debug_mode = 1
from soundrts.mapfile import Map

config.mods = ""

from soundrts import clientmain

if __name__ == "__main__":
    clientmain.init_media()

    # map = "multi/pra2.txt"
    map = "multi/jl5.txt"
    # map = "multi/jl4"

    # players = ["test", "easy"], ["random_faction", "random_faction"], ["1", "2"]
    # players = ["test", "aggressive"], ["random_faction", "random_faction"], ["1", "2"]
    players = (
        ["test", "aggressive", "easy"],
        ["random_faction", "random_faction", "random_faction"],
        ["1", "1", "2"],
    )

    try:
        clientmain.TrainingGame(Map(map), *players).run(speed=20)
    except:
        input(f"\n{traceback.format_exc()}\n[press Enter to quit]")
