import re
from ast import literal_eval

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # Python < 3.11 with dependency installed
    except ModuleNotFoundError:
        tomllib = None

d = {}


class _FallbackTOMLDecodeError(ValueError):
    pass


def _strip_comments(line: str) -> str:
    in_string = False
    escaped = False
    for i, ch in enumerate(line):
        if ch == "\\" and in_string:
            escaped = not escaped
            continue
        if ch == '"' and not escaped:
            in_string = not in_string
        if ch == "#" and not in_string:
            return line[:i]
        escaped = False
    return line


def _parse_simple_value(value: str):
    value = re.sub(r"\btrue\b", "True", value, flags=re.I)
    value = re.sub(r"\bfalse\b", "False", value, flags=re.I)
    return literal_eval(value)


def _load_minimal_toml(path: str):
    data = {}
    current = data
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = _strip_comments(raw).strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1].strip()
                if not section:
                    raise _FallbackTOMLDecodeError(f"empty table name on line {lineno}")
                current = data.setdefault(section, {})
                if not isinstance(current, dict):
                    raise _FallbackTOMLDecodeError(
                        f"invalid table assignment on line {lineno}"
                    )
                continue
            if "=" not in line:
                raise _FallbackTOMLDecodeError(f"invalid line {lineno}: {raw.rstrip()}")
            key, value = (part.strip() for part in line.split("=", 1))
            if not key:
                raise _FallbackTOMLDecodeError(f"missing key on line {lineno}")
            try:
                current[key] = _parse_simple_value(value)
            except Exception as exc:
                raise _FallbackTOMLDecodeError(
                    f"invalid value for '{key}' on line {lineno}"
                ) from exc
    return data


def load():
    global d
    try:
        if tomllib is not None:
            with open("cfg/parameters.toml", "rb") as f:
                d = tomllib.load(f)
        else:
            d = _load_minimal_toml("cfg/parameters.toml")
    except Exception as exc:
        decode_error = getattr(tomllib, "TOMLDecodeError", _FallbackTOMLDecodeError)
        if isinstance(exc, (decode_error, _FallbackTOMLDecodeError)):
            print("error in parameters.toml")
        else:
            raise


load()
