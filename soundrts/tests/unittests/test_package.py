from soundrts.lib.package import Package, PackageStack


def test_zip_package():
    p = Package.from_path("soundrts/tests/res2.zip")

    assert p.subpackage("mods/mod1") is not None
    assert p.subpackage("mods/mod") is None
    assert p.subpackage("mods/mod11") is None

    assert next(p.relative_paths_of_files_in_subtree("mods")).startswith("mods")

    assert set(p.dirnames()) == {"mods"}

    assert p.isdir("mods")
    assert not p.isfile("mods")
    assert p.isfile("mods/mod1/rules.txt")
    assert not p.isdir("mods/mod1/rules.txt")
    assert p.isfile("readme.txt")
    assert not p.isdir("readme.txt")


def test_folder_package():
    p = Package.from_path("soundrts/tests/res2")

    assert p.subpackage("mods/mod1") is not None
    assert p.subpackage("mods/mod") is None
    assert p.subpackage("mods/mod11") is None

    assert next(p.relative_paths_of_files_in_subtree("mods")).startswith("mods")

    assert set(p.dirnames()) == {"mods"}

    assert p.isdir("mods")
    assert not p.isfile("mods")
    assert p.isfile("mods/mod1/rules.txt")
    assert not p.isdir("mods/mod1/rules.txt")
    assert p.isfile("readme.txt")
    assert not p.isdir("readme.txt")


def test_res_folder_package():
    p = Package.from_path("soundrts/tests/res")

    assert p.subpackage("ui") is not None
    assert p.subpackage("u") is None
    assert p.subpackage("ui1") is None

    assert next(p.relative_paths_of_files_in_subtree("ui")).startswith("ui")
    assert set(p.dirnames()) == {"ui", "ui-fr", "multi"}


def test_subpackage_dirnames():
    for ext in [".zip", ""]:
        p = Package.from_path("soundrts/tests/res2" + ext)
        mods = p.subpackage("mods")
        assert set(mods.dirnames()) == {"mod1", "sound1", "mod2"}
        assert mods.subpackage("sound1").is_a_soundpack()
        assert not mods.subpackage("mod1").is_a_soundpack()
        assert len(PackageStack(["soundrts/tests/res2" + ext]).mods()) == len({"mod1", "sound1", "mod2"})
