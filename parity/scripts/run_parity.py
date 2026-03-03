from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from swgoh_comlink import StatCalc

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_GAMEDATA_URL = (
    "https://raw.githubusercontent.com/swgoh-utils/gamedata/main/gameData.json"
)
JS_RUNNER = ROOT / "parity" / "scripts" / "run_js_parity.js"


def _max_numeric_key(d: dict[str, Any]) -> int:
    return max(int(k) for k in d.keys())


def _build_mods(mod_set_ids: list[int]) -> list[dict[str, Any]]:
    mods: list[dict[str, Any]] = []
    for i in range(6):
        set_id = mod_set_ids[i % len(mod_set_ids)]
        mods.append(
            {
                "set": set_id,
                "level": 15,
                "pips": 6,
                "tier": 5,
                "primaryStat": {"unitStat": 5, "value": 10 + i},
                "secondaryStat": [
                    {"unitStat": 53, "value": 1.5},
                    {"unitStat": 1, "value": 1000 + i * 20},
                ],
            }
        )
    return mods


def _build_char(
    unit_data: dict[str, Any], mod_set_ids: list[int], unit_id: str
) -> dict[str, Any]:
    meta = unit_data[unit_id]
    rarity = _max_numeric_key(meta["growthModifiers"])
    gear = _max_numeric_key(meta["gearLvl"])
    gear_def = meta["gearLvl"][str(gear)]
    gear_ids = [gid for gid in gear_def.get("gear", []) if int(gid) < 9990]

    relic_tier = None
    relic_entries = meta.get("relic") or []
    if len(relic_entries) > 3:
        relic_tier = min(5, len(relic_entries) - 1)

    return {
        "defId": unit_id,
        "rarity": rarity,
        "level": 85,
        "gear": gear,
        "equipped": [
            {"equipmentId": gid, "slot": idx} for idx, gid in enumerate(gear_ids[:6])
        ],
        "skills": [
            {"id": s["id"], "tier": s["maxTier"]} for s in meta.get("skills", [])
        ],
        "mods": _build_mods(mod_set_ids),
        "relic": {"currentTier": relic_tier} if relic_tier else None,
    }


def _select_units(unit_data: dict[str, Any]) -> tuple[str, str]:
    char_ids = sorted(
        uid for uid, meta in unit_data.items() if meta.get("combatType") == 1
    )
    ship_ids = sorted(
        uid
        for uid, meta in unit_data.items()
        if meta.get("combatType") == 2 and len(meta.get("crew", [])) > 0
    )
    if not char_ids:
        raise RuntimeError("No character units found in game data")
    if not ship_ids:
        raise RuntimeError("No crewed ship units found in game data")
    return char_ids[0], ship_ids[0]


def _build_fixtures(game_data: dict[str, Any]) -> dict[str, Any]:
    unit_data = game_data["unitData"]
    mod_set_ids = sorted(int(k) for k in game_data["modSetData"].keys())

    char_id, ship_id = _select_units(unit_data)
    char = _build_char(unit_data, mod_set_ids, char_id)

    ship_meta = unit_data[ship_id]
    ship_rarity = _max_numeric_key(ship_meta["growthModifiers"])
    ship = {
        "defId": ship_id,
        "rarity": ship_rarity,
        "level": 85,
        "skills": [
            {"id": s["id"], "tier": s["maxTier"]} for s in ship_meta.get("skills", [])
        ],
    }

    crew = [_build_char(unit_data, mod_set_ids, cid) for cid in ship_meta["crew"]]

    roster = (
        [copy.deepcopy(char)] + [copy.deepcopy(c) for c in crew] + [copy.deepcopy(ship)]
    )
    players = [{"roster": copy.deepcopy(roster)}]

    return {
        "char": char,
        "ship": ship,
        "crew": crew,
        "roster": roster,
        "players": players,
    }


def _run_python(fixtures: dict[str, Any], game_data: dict[str, Any]) -> dict[str, Any]:
    calc = StatCalc(game_data)

    char_unit = copy.deepcopy(fixtures["char"])
    char_stats = calc.calc_char_stats(char_unit)

    crew_units = copy.deepcopy(fixtures["crew"])
    for c in crew_units:
        c["gp"] = calc.calc_char_gp(c)
    ship_unit = copy.deepcopy(fixtures["ship"])
    ship_stats = calc.calc_ship_stats(ship_unit, crew_units)

    roster = copy.deepcopy(fixtures["roster"])
    roster_count = calc.calc_roster_stats(roster)

    players = copy.deepcopy(fixtures["players"])
    player_count = calc.calc_player_stats(players)

    return {
        "char": {
            "stats": char_stats,
            "gp": char_unit.get("gp"),
            "unit": char_unit,
        },
        "ship": {
            "stats": ship_stats,
            "gp": ship_unit.get("gp"),
            "unit": ship_unit,
            "crew": crew_units,
        },
        "roster": {
            "count": roster_count,
            "units": roster,
        },
        "players": {
            "count": player_count,
            "players": players,
        },
    }


def _run_js(fixtures: dict[str, Any], game_data_path: Path) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tf:
        json.dump(fixtures, tf)
        fixtures_path = Path(tf.name)

    try:
        proc = subprocess.run(
            ["node", str(JS_RUNNER), str(game_data_path), str(fixtures_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        fixtures_path.unlink(missing_ok=True)

    return json.loads(proc.stdout)


def _normalize_game_data(payload: dict[str, Any]) -> dict[str, Any]:
    if "unitData" in payload:
        return payload
    if (
        "data" in payload
        and isinstance(payload["data"], dict)
        and "unitData" in payload["data"]
    ):
        return payload["data"]
    raise ValueError("Unsupported gameData payload format")


def _compare(lhs: Any, rhs: Any, path: str = "$", tol: float = 1e-9) -> list[str]:
    errors: list[str] = []

    if isinstance(lhs, (int, float)) and isinstance(rhs, (int, float)):
        if abs(float(lhs) - float(rhs)) > tol:
            errors.append(f"{path}: {lhs} != {rhs}")
        return errors

    if not isinstance(lhs, type(rhs)):
        errors.append(
            f"{path}: type mismatch {type(lhs).__name__} != {type(rhs).__name__}"
        )
        return errors

    if isinstance(lhs, dict):
        lkeys = set(lhs.keys())
        rkeys = set(rhs.keys())
        for missing in sorted(lkeys - rkeys):
            errors.append(f"{path}: missing key in rhs: {missing}")
        for missing in sorted(rkeys - lkeys):
            errors.append(f"{path}: missing key in lhs: {missing}")
        for key in sorted(lkeys & rkeys):
            errors.extend(_compare(lhs[key], rhs[key], f"{path}.{key}", tol))
        return errors

    if isinstance(lhs, list):
        if len(lhs) != len(rhs):
            errors.append(f"{path}: list length mismatch {len(lhs)} != {len(rhs)}")
            return errors
        for idx, (lv, rv) in enumerate(zip(lhs, rhs)):
            errors.extend(_compare(lv, rv, f"{path}[{idx}]", tol))
        return errors

    if lhs != rhs:
        errors.append(f"{path}: {lhs!r} != {rhs!r}")
    return errors


def _load_game_data(gamedata: str) -> tuple[dict[str, Any], Path]:
    if gamedata.startswith("http://") or gamedata.startswith("https://"):
        with urllib.request.urlopen(gamedata, timeout=30) as response:
            data = _normalize_game_data(json.loads(response.read().decode("utf-8")))
        cache_path = ROOT / "parity" / ".cache-gameData.json"
        cache_path.write_text(json.dumps(data), encoding="utf-8")
        return data, cache_path

    gamedata_path = Path(gamedata)
    data = _normalize_game_data(json.loads(gamedata_path.read_text(encoding="utf-8")))
    return data, gamedata_path


def run(gamedata: str = DEFAULT_GAMEDATA_URL) -> int:
    game_data, gamedata_path = _load_game_data(gamedata)
    fixtures = _build_fixtures(game_data)

    py_out = _run_python(fixtures, game_data)
    js_out = _run_js(fixtures, gamedata_path)

    diffs = _compare(py_out, js_out)
    if diffs:
        print("Parity mismatch detected:", file=sys.stderr)
        for diff in diffs[:50]:
            print(f"- {diff}", file=sys.stderr)
        if len(diffs) > 50:
            print(f"... and {len(diffs) - 50} more", file=sys.stderr)
        return 1

    print("Parity OK: Python output matches JS baseline for generated fixtures.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run JS vs Python parity harness")
    parser.add_argument("--gamedata", default=DEFAULT_GAMEDATA_URL)
    args = parser.parse_args()
    return run(args.gamedata)


if __name__ == "__main__":
    raise SystemExit(main())
