try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

d = {}


def load():
    global d
    try:
        with open("cfg/parameters.toml", "rb") as f:
            d = tomllib.load(f)
    except tomllib.TOMLDecodeError:
        print("error in parameters.toml")


load()
