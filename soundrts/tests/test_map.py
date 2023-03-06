from pathlib import Path

from soundrts.game import MultiplayerGame
from soundrts.lib.resource import res
from soundrts.lib.package import Package
from soundrts.mapfile import Map
from soundrts.pack import pack_file_or_folder, pack_buffer
from soundrts.world import World
from soundrts.worldclient import Coordinator


def test_sync_error():
    m = Map("soundrts/tests/jl1.txt")
    main_server = None
    game = MultiplayerGame(m, [("test", 1, "faction")], "test", main_server, 0, 1)
    c: Coordinator = game.players[0]
    c.world = World()
    c.world.load_and_build_map(m)
    c.world.update()
    c.get_sync_debug_msg_1()
    c.get_sync_debug_msg_2()
    c.world.update()
    c.get_sync_debug_msg_1()
    c.get_sync_debug_msg_2()

#        print c.get_sync_debug_msg_1()
#        print c.get_sync_debug_msg_2()


def test_nb_players_after_unpack():
    for n in ["jl1.txt", "jl4.zip"]:
        m = res.unpack_map(pack_file_or_folder(f"soundrts/tests/{n}"))
        assert m.nb_players_min == 2
        assert m.name == Path(n).stem


def test_pkg_map_inside_pkg():
    package = Package.from_path("soundrts/tests/res.zip")
    b = package.open_binary("multi/jl4.zip").read()
    multi = package.subpackage("multi")
    assert multi.open_binary("jl4.zip").read() == b
    loaded = Map.load(package.open_binary("multi/jl4.zip"), "jl4.zip")

    packed_buffer = pack_buffer(b, "jl4.zip")
    unpacked = res.unpack_map(packed_buffer)
    assert unpacked.definition == loaded.definition
