import soundrts.msgparts as mp
from soundrts import clientservermenu as csm

# def test_start_game_args():
#    m = csm._BeforeGameMenu(None)
#    m.map = Map("soundrts/tests/jl1.txt")
#    m.srv_start_game(["me,1,orc;ai_easy,2,random_faction", "me", 0, 1])


def test_game_status():
    assert csm.game_short_status("jl1", "0,1", "1")


def test_insert_silences():
    s = mp.PERIOD[0]
    insert_silences = csm.insert_silences
    assert insert_silences([]) == []
    assert insert_silences([1000]) == [1000]
    assert insert_silences([100, 50]) == [100, s, 50]
    assert insert_silences([100, 50, 20]) == [100, s, 50, s, 20]
