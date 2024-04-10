import pytest

from swgoh_comlink import SwgohComlink


def test_get_gac_global_leaderboard():
    comlink = SwgohComlink()
    gac_kyber_2_lb = comlink.get_gac_leaderboard(leaderboard_type=6, league=100, division=20)
    assert "player" in gac_kyber_2_lb.keys()

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type=6, league=101)

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type=6, division=101)

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type=2)

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type="6")


def test_get_gac_brackets_leaderboard():
    comlink = SwgohComlink()
    current_event_instance = None
    current_events = comlink.get_events()
    for event in current_events["gameEvent"]:
        if event["type"] == 10:
            current_event_instance = f"{event['id']}:{event['instance'][0]['id']}"
    league = "KYBER"
    group_id = f"{current_event_instance}:{league}:0"

    gac_kyber_2_lb = comlink.get_gac_leaderboard(leaderboard_type=4,
                                                 event_instance_id=current_event_instance,
                                                 group_id=group_id)
    assert "player" in gac_kyber_2_lb.keys()

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type=4,
                                    event_instance_id="UNKNOWN", )

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type=4,
                                    group_id="UNKNOWN", )

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type=4, league=101)

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type=4, division=101)

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type=2)

    with pytest.raises(ValueError):
        comlink.get_gac_leaderboard(leaderboard_type="4")
