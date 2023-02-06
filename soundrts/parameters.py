import tomli

d = {}


def load():
    global d
    try:
        with open("cfg/parameters.toml", "rb") as f:
            d = tomli.load(f)
    except tomli.TOMLDecodeError:
        print("error in parameters.toml")


load()
