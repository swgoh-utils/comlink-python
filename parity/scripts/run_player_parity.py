from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any

from swgoh_comlink import StatCalc

ROOT = Path(__file__).resolve().parents[2]


DEFAULT_GAMEDATA_URL = (
    "https://raw.githubusercontent.com/swgoh-utils/gamedata/main/gameData.json"
)
DEFAULT_PLAYER = ROOT / "tests" / "resources" / "example-player.json"
JS_RUNNER = ROOT / "parity" / "scripts" / "run_js_player_parity.js"


def _run_python(player: dict[str, Any], game_data: dict[str, Any]) -> dict[str, Any]:
    calc = StatCalc(game_data)
    payload = _sanitize_player(player, game_data)
    count = calc.calc_player_stats(payload)
    return {"count": count, "player": payload}


def _run_js(player_path: Path, game_data_path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["node", str(JS_RUNNER), str(game_data_path), str(player_path)],
        check=True,
        capture_output=True,
        text=True,
    )
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


def run(player_path: Path, gamedata: str = DEFAULT_GAMEDATA_URL) -> int:
    game_data, game_data_path = _load_game_data(gamedata)
    player = json.loads(player_path.read_text(encoding="utf-8"))

    py_out = _run_python(player, game_data)
    js_out = _run_js(player_path, game_data_path)

    diffs = _compare(py_out, js_out)
    if diffs:
        print("Player parity mismatch detected:", file=sys.stderr)
        for diff in diffs[:50]:
            print(f"- {diff}", file=sys.stderr)
        if len(diffs) > 50:
            print(f"... and {len(diffs) - 50} more", file=sys.stderr)
        return 1

    print(
        "Player parity OK: Python output matches JS baseline for "
        "example player rosterUnit payload."
    )
    return 0


def _get_def_id(unit: dict[str, Any]) -> str:
    return str(unit.get("definitionId", "")).split(":")[0]


def _table_get(table: Any, key: Any, default: Any = None) -> Any:
    if table is None:
        return default
    if isinstance(table, list):
        try:
            idx = int(key)
        except (TypeError, ValueError):
            return default
        return table[idx] if 0 <= idx < len(table) else default
    if key in table:
        return table[key]
    skey = str(key)
    if skey in table:
        return table[skey]
    try:
        ikey = int(key)
    except (TypeError, ValueError):
        return default
    return table.get(ikey, default)


def _sanitize_player(
    player: dict[str, Any], game_data: dict[str, Any]
) -> dict[str, Any]:
    payload = copy.deepcopy(player)
    roster = payload.get("rosterUnit", [])
    if not isinstance(roster, list):
        payload["rosterUnit"] = []
        return payload

    unit_data = game_data["unitData"]
    sanitized: list[dict[str, Any]] = []
    for unit in roster:
        def_id = _get_def_id(unit)
        meta = unit_data.get(def_id)
        if not meta:
            continue

        relic = unit.get("relic")
        if relic and relic.get("currentTier", 0) > 2:
            relic_map = meta.get("relic", [])
            if isinstance(relic_map, dict):
                keys = [int(k) for k in relic_map.keys() if str(k).isdigit()]
                max_relic_tier = max(keys) if keys else -1
            else:
                max_relic_tier = len(relic_map) - 1
            if max_relic_tier < 3:
                relic["currentTier"] = 2
            elif relic["currentTier"] > max_relic_tier:
                relic["currentTier"] = max_relic_tier
            relic_def = _table_get(relic_map, relic["currentTier"])
            if not relic_def or str(relic_def) not in game_data["relicData"]:
                relic["currentTier"] = 2

        skill_defs = meta.get("skills", [])
        skill_by_id = {s.get("id"): s for s in skill_defs if s.get("id")}
        sanitized_skills = []
        for skill in unit.get("skill", []) or []:
            skill_def = skill_by_id.get(skill.get("id"))
            if not skill_def:
                continue
            next_skill = dict(skill)
            max_tier = int(skill_def.get("maxTier", next_skill.get("tier", 1)))
            tier = int(next_skill.get("tier", 1))
            if tier > max_tier:
                tier = max_tier
            if tier < 1:
                tier = 1
            next_skill["tier"] = tier
            sanitized_skills.append(next_skill)
        unit["skill"] = sanitized_skills

        sanitized.append(unit)

    payload["rosterUnit"] = sanitized
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run JS vs Python parity for example player"
    )
    parser.add_argument("--gamedata", default=DEFAULT_GAMEDATA_URL)
    parser.add_argument("--player", type=Path, default=DEFAULT_PLAYER)
    args = parser.parse_args()
    return run(args.player, args.gamedata)


if __name__ == "__main__":
    raise SystemExit(main())
