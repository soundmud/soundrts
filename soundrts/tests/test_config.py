import os

import pytest

from soundrts import config
from soundrts.config import login_is_valid


def test_login_is_valid():
    assert login_is_valid("a")
    assert login_is_valid("a" * 20)
    assert not login_is_valid("a" * 21)
    assert not login_is_valid("")
    assert not login_is_valid("a ")
    assert login_is_valid("a2")
    assert not login_is_valid("wrong-login")


@pytest.fixture
def cfg():
    config.login = None
    config.num_channels = None
    config.timeout = None


def test_load_defaults_if_file_doesnt_exist(cfg):
    n = "soundrts/tests/not_a_file.ini"
    try:
        os.unlink(n)
    except:
        pass
    config.load(n)
    assert config.login == "player"
    assert config.num_channels == 16
    assert config.timeout == 60.0
    os.unlink(n)


def test_load_file_with_changes(cfg):
    config.load("soundrts/tests/config_with_changes.ini")
    assert config.login == "test"
    assert config.num_channels == 32
    assert config.timeout == 200.0
    config.load("soundrts/tests/config_with_changes.ini")
    assert config.login == "test"
    assert config.num_channels == 32
    assert config.timeout == 200.0


def test_load_defaults_if_file_with_errors(cfg):
    n = "soundrts/tests/config_with_errors.ini"
    o = n + ".old"
    try:
        os.unlink(o)
    except:
        pass
    s = open(n).read()
    try:
        config.load(n)
        assert s != open(n).read()
    finally:
        open(n, "w").write(s)
        assert s == open(n).read()
    assert config.login == "player"
    assert config.num_channels == 16
    assert config.timeout == 60.0
    assert config.mods == ""
    os.unlink(o)


def test_load_and_save(cfg):
    n2 = "soundrts/tests/config_with_changes2.ini"
    config.load("soundrts/tests/config_with_changes.ini")
    assert config.login == "test"
    assert config.num_channels == 32
    assert config.timeout == 200.0
    config.login = "a"
    config.num_channels = 1
    config.timeout = 1.0
    config.save(n2)
    config.login = "b"
    config.num_channels = 2
    config.timeout = 1.1
    config.load(n2)
    assert config.login == "a"
    assert config.num_channels == 1
    assert config.timeout == 1.0
    os.unlink(n2)
