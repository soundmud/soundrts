import base64
import io
import os

from soundrts.lib import zipdir

SEPARATOR = b"***"


def unpack_file(bytes_: bytes):
    encoded_name, encoded_buffer = bytes_.split(SEPARATOR, 1)
    name: str = encoded_name.decode(encoding="utf-8", errors="replace")
    buffer: bytes = base64.b64decode(encoded_buffer)
    return buffer, name


def pack_file_or_folder(path) -> bytes:
    if os.path.isfile(path):
        name, buffer = _pack_file(path)
    else:
        name, buffer = _pack_folder(path)
    return pack_buffer(buffer, name)


def _pack_file(path):
    n = os.path.split(path)[-1]
    with open(path, "rb") as f:
        b = f.read()
    return n, b


def _pack_folder(path):
    n = os.path.split(path)[-1] + ".zip"
    f = io.BytesIO()
    zipdir.zipdir(path, f)
    b = f.getvalue()
    return n, b


def pack_buffer(buffer, name):
    encoded_name = name.encode(encoding="utf-8", errors="replace")
    encoded_buffer = base64.b64encode(buffer)
    return encoded_name + SEPARATOR + encoded_buffer
