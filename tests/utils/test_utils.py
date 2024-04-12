# coding=utf-8
"""
Test swgoh_comlink.utils functions
"""
import json
import os.path
import sys
import time
from pathlib import Path

import pytest

from swgoh_comlink import SwgohComlink, SwgohComlinkAsync
from swgoh_comlink.constants import NotGiven
from swgoh_comlink.utils import (
    func_debug_logger,
    human_time,
    sanitize_allycode,
    convert_league_to_int,
    convert_divisions_to_int,
    convert_relic_tier,
    get_function_name,
    get_guild_members,
    validate_file_path,
    get_tw_omicrons,
    get_current_datacron_sets,
    create_localized_unit_name_dictionary,
    func_timer,
    get_async_events,
    load_master_map,
    search_gac_brackets,
)

test_dir = Path('/Users/marktripod/code/comlink-python/tests')

with open(f"{test_dir}/master/skills.json") as fn:
    _skills: list = json.load(fn)

with open(f"{test_dir}/master/result_skills.json") as fn:
    _result_skills: list = json.load(fn)

with open(f"{test_dir}/master/name_key_result.json") as fn:
    _name_key_results: dict = json.load(fn)

with open(f"{test_dir}/master/eng_us_units.txt") as fn:
    _eng_us_txt: list = fn.readlines()

bin_eng_us: list = [x.encode() for x in _eng_us_txt]
eng_us_str: str = "".join(_eng_us_txt)

async_comlink = SwgohComlinkAsync(default_logger_enabled=True)
comlink = SwgohComlink(default_logger_enabled=True)


def get_dc_sets() -> list[dict[str, str]]:
    game_data_segment4 = comlink.get_game_data(include_pve_units=False, request_segment=4)
    return [{"id": x['id'], "expirationTimeMs": x['expirationTimeMs']} for x in game_data_segment4['datacronSet']]


_dc_sets: list[dict[str, str]] = get_dc_sets()


def get_dc_current_sets(dc_sets: list) -> list[dict[str, str]]:
    import math
    import time
    current_time_ms = int(math.floor(time.time() * 1000))
    current_dc_set: list = []
    for dc_set in dc_sets:
        if int(dc_set['expirationTimeMs']) >= current_time_ms:
            current_dc_set.append(dc_set)
    return current_dc_set


_dc_results: list[dict[str, str]] = get_dc_current_sets(_dc_sets)


@pytest.fixture
def create_temp_file() -> str:
    """Create a temporary file for use in validating utility functions"""
    d = test_dir / "temp_files"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "tmp_file.txt"
    p.write_text("test file", encoding="utf-8")
    yield p
    p.unlink()
    d.rmdir()


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (0, "1970-01-01 00:00:00"),
        (1708898400000, "2024-02-25 22:00:00"),
        ("1708898400000", "2024-02-25 22:00:00"),
        (1711317600.99999, "2024-03-24 22:00:00"),
    ],
)
def test_human_time(test_input, expected):
    assert human_time(test_input) == expected


def test_human_time_no_input():
    with pytest.raises(ValueError):
        human_time()


def test_human_time_large_input():
    default_max_str_limit = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(640)
    with pytest.raises(ValueError):
        human_time('2' * 5432)
    sys.set_int_max_str_digits(default_max_str_limit)


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (123456789, "123456789"),
        ("123456789", "123456789"),
        ("123-456-789", "123456789"),
        (1234567890, "exception:ValueError"),
        (None, ""),
    ],
)
def test_sanitize_allycode(test_input, expected):
    if 'exception' in expected:
        with pytest.raises(ValueError):
            sanitize_allycode(test_input)
    else:
        assert sanitize_allycode(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (0, "LOCKED"),
        ("10", "9"),
        (-1, NotGiven),
        (NotGiven, "exception"),
    ],
)
def test_convert_relic_tier(test_input, expected):
    if expected == "exception":
        with pytest.raises(ValueError):
            convert_relic_tier(test_input)
    elif expected is NotGiven:
        assert convert_relic_tier(test_input) is None
    else:
        assert convert_relic_tier(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (1, 25),
        ("4", 10),
        ("6", None),
    ],
)
def test_convert_division_to_int(test_input, expected):
    if expected is None:
        assert convert_divisions_to_int(test_input) is expected
    else:
        assert convert_divisions_to_int(test_input) == expected


@func_debug_logger
def test_convert_division_to_int_no_arg():
    with pytest.raises(ValueError):
        convert_divisions_to_int()


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ("Kyber", 100),
        ("carbonite", 20),
        ("unknown", None),
    ],
)
def test_convert_league_to_int(test_input, expected):
    if expected is None:
        assert convert_league_to_int(test_input) is expected
    else:
        assert convert_league_to_int(test_input) == expected


def test_convert_league_to_int_no_arg():
    with pytest.raises(ValueError):
        convert_league_to_int()


def test_get_guild_members_by_allycode():
    guild_members = get_guild_members(comlink, allycode=314927874)
    assert isinstance(guild_members, list)
    assert "playerId" in guild_members[0].keys()


def test_get_guild_members_by_allycode_async():
    guild_members = get_guild_members(comlink, allycode=314927874)
    assert isinstance(guild_members, list)
    assert "playerId" in guild_members[0].keys()


def test_get_guild_members_by_player_id(player_id):
    guild_members = get_guild_members(comlink, player_id=player_id)
    assert isinstance(guild_members, list)
    assert "playerId" in guild_members[0].keys()


def test_get_guild_members_by_player_id_async(player_id):
    guild_members = get_guild_members(comlink, player_id=player_id)
    assert isinstance(guild_members, list)
    assert "playerId" in guild_members[0].keys()


def test_get_guild_members_none():
    with pytest.raises(ValueError):
        get_guild_members(comlink=comlink)


def test_get_guild_members_none_async():
    with pytest.raises(ValueError):
        get_guild_members(comlink=comlink)


def test_get_guild_members_no_comlink(player_id):
    with pytest.raises(ValueError):
        get_guild_members(player_id=player_id)


def test_validate_path(create_temp_file):
    test_path = os.path.join(test_dir, "master", "skills.json")
    assert validate_file_path(test_path) is True
    assert validate_file_path(create_temp_file) is True


def test_validate_path_no_path():
    with pytest.raises(ValueError):
        validate_file_path()


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (_skills, _result_skills),
        ([], []),
        ("unknown", "exception:ValueError"),
    ],
)
def test_get_tw_omicrons(test_input, expected):
    if 'exception' in expected:
        with pytest.raises(ValueError):
            get_tw_omicrons(test_input)

    elif expected is None:
        assert get_tw_omicrons(test_input) is None
    else:
        assert get_tw_omicrons(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (_dc_sets, _dc_results),
        ([], []),
        ("unknown", "exception:ValueError"),
    ],
)
def test_get_current_datacron_sets(test_input, expected):
    if 'exception' in expected:
        with pytest.raises(ValueError):
            get_current_datacron_sets(test_input)

    elif expected is None:
        assert get_current_datacron_sets(test_input) is None
    else:
        assert get_current_datacron_sets(test_input) == expected


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (_eng_us_txt, _name_key_results),
        (eng_us_str, _name_key_results),
        (bin_eng_us, _name_key_results),
        ([], {}),
        ({}, "exception"),
    ],
)
def test_create_localized_unit_name_dictionary(test_input, expected):
    if expected == 'exception':
        with pytest.raises(ValueError):
            create_localized_unit_name_dictionary(test_input)

    elif expected is None:
        assert create_localized_unit_name_dictionary(test_input) is None
    else:
        assert create_localized_unit_name_dictionary(test_input) == expected


def test_func_timer_decorator():
    @func_timer
    def function_to_time():
        time.sleep(3)
        return "completed"

    assert function_to_time() == "completed"


def test_func_debug_logger_decorator():
    def function_to_time():
        time.sleep(3)
        return "completed"

    assert function_to_time() == "completed"


@pytest.mark.asyncio
async def test_get_async_events():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    p = await get_async_events(comlink=async_comlink)
    assert "gameEvent" in p.keys()


@pytest.mark.asyncio
async def test_get_async_events_no_comlink():
    comlink.logger.debug(f"** Starting {get_function_name()} with no comlink instance.")
    with pytest.raises(ValueError):
        await get_async_events()


@pytest.mark.asyncio
async def test_get_async_events_wrong_comlink():
    comlink.logger.debug(f"** Starting {get_function_name()} with wrong comlink instance type.")
    with pytest.raises(ValueError):
        await get_async_events(comlink=comlink)


def test_search_gac_brackets():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    gac_brackets: dict = {
        0: [
            {'name': 'Habsfan'},
            {'name': 'DarthRevan1016'},
            {'name': 'DIPOLE DIPOLE'},
            {'name': 'Inept'},
            {'name': 'BluntForceTrauma'},
            {'name': 'PapaPalpatine'},
            {'name': 'Sanders28'},
            {'name': 'Rui Vuusen'}
        ],
        1: [
            {'name': 'Mail'},
            {'name': 'Матвей'},
            {'name': 'Zarseem Dyartes'},
            {'name': 'Austin69surmom'},
            {'name': 'Sawyer1601'},
            {'name': 'ARMOURS'},
            {'name': 'Chewbie'},
            {'name': 'Oss Wilum'}
        ],
        2: [
            {'name': 'Aesop Rock'},
            {'name': 'Cyruss'},
            {'name': 'Sashaisha'},
            {'name': 'Tassenix'},
            {'name': 'valisa nisira'},
            {'name': 'Merrick'},
            {'name': 'Mech gold'},
            {'name': 'Exxcuser'}
        ]
    }
    search_result = search_gac_brackets(gac_brackets=gac_brackets, player_name="Merrick")
    assert search_result['bracket'] == 2

    search_result = search_gac_brackets(gac_brackets=gac_brackets, player_name="Sawyer1601")
    assert search_result['bracket'] == 1

    search_result = search_gac_brackets(gac_brackets=gac_brackets, player_name="Inept")
    assert search_result['bracket'] == 0

    search_result = search_gac_brackets(gac_brackets=gac_brackets, player_name="Mickey Mouse")
    assert search_result == {}


def test_load_master_map():
    comlink.logger.debug(f"** Starting {get_function_name()}")
    master_map = load_master_map(test_dir)
    assert isinstance(master_map, list)
    assert len(master_map) > 0

    master_map = load_master_map(test_dir, "fre_fr")
    assert isinstance(master_map, list)
    assert len(master_map) > 0

    master_map = load_master_map(master_map_path=test_dir, language="")
    assert master_map is None

    master_map = load_master_map(master_map_path="/tmp")
    assert master_map is None