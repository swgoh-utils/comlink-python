from __future__ import annotations

import copy
import json
import logging
import math
import urllib.request
from typing import Any

from ..helpers._stat_data import STATS as _CANONICAL_STATS


class StatCalc:
    """SWGOH stat calculator

    Args:
        game_data: Optional preloaded game data payload. If omitted, the
            calculator fetches the latest payload from the swgoh-utils
            GitHub game data repository.
    """

    _FIXED_GAME_STYLE = True
    _FIXED_PERCENT_VALS = True
    _FIXED_CALC_GP = True

    _DEFAULT_GAMEDATA_URL = "https://raw.githubusercontent.com/swgoh-utils/gamedata/main/gameData.json"
    _LOGGER = logging.getLogger(__name__)

    STATS_NAME_MAP: dict[str, dict[str, Any]] = _CANONICAL_STATS

    def __init__(self, game_data: dict[str, Any] | None = None) -> None:
        """Initialize a calculator instance.

        Args:
            game_data: Optional game data payload to load immediately.
        """
        self._unit_data: dict[str, Any] | None = None
        self._mod_set_data: dict[str, Any] | None = None
        self._gear_data: dict[str, Any] | None = None
        self._cr_tables: dict[str, Any] | None = None
        self._gp_tables: dict[str, Any] | None = None
        self._relic_data: dict[str, Any] | None = None

        if game_data is None:
            self._LOGGER.info("No game data provided, loading from GitHub")
            game_data = self._fetch_game_data_from_github()
        else:
            self._LOGGER.debug("Using caller-provided game data")
        self.set_game_data(game_data)

    def set_game_data(self, game_data: dict[str, Any]) -> None:
        """Set or replace the game data used by this calculator.

        Args:
            game_data: Game data payload containing unit, gear, CR, GP, relic,
                and mod set tables.
        """
        self._unit_data = game_data["unitData"]
        self._gear_data = game_data["gearData"]
        self._mod_set_data = game_data["modSetData"]
        self._cr_tables = game_data["crTables"]
        self._gp_tables = game_data["gpTables"]
        self._relic_data = game_data["relicData"]
        assert self._unit_data is not None
        assert self._gear_data is not None
        assert self._mod_set_data is not None
        self._LOGGER.info(
            "Game data loaded: units=%d gear=%d mod_sets=%d",
            len(self._unit_data),
            len(self._gear_data),
            len(self._mod_set_data),
        )

    def calc_char_stats(self, unit: dict[str, Any]) -> dict[str, Any]:
        """Calculate stats and GP for a character unit.

        Args:
            unit: Character object in either normalized (`defId`) or raw game
                format (`definitionId`).

        Returns:
            The input unit with `stats` and `gp` keys added, containing the calculated stats and GP.
        """
        self._require_game_data()
        self._LOGGER.debug("Calculating character stats")
        char = self._normalize_char(unit)

        stats: dict[str, Any] = self._get_char_raw_stats(char)
        stats = self._calculate_base_stats(stats, char["level"], char["defId"])
        stats["mods"] = self._calculate_mod_stats(stats["base"], char)
        stats = self._format_stats(stats, char["level"])

        stats = self._rename_stats(stats)

        unit["stats"] = stats

        if self._FIXED_CALC_GP:
            unit["gp"] = self._calc_char_gp(char)
            stats["gp"] = unit["gp"]

        return unit

    def calc_ship_stats(self, unit: dict[str, Any], crew_member: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate stats and GP for a ship unit.

        Args:
            unit: Ship object in either normalized (`defId`) or raw game format.
            crew_member: Crew member list for the ship.

        Returns:
            The input unit with `stats` and `gp` keys added, containing the calculated stats and GP.
        """
        self._require_game_data()
        self._LOGGER.debug("Calculating ship stats with %d crew", len(crew_member))
        ship, crew = self._normalize_ship_and_crew(unit, crew_member)

        stats: dict[str, Any] = self._get_ship_raw_stats(ship, crew)
        stats = self._calculate_base_stats(stats, ship["level"], ship["defId"])
        stats = self._format_stats(stats, ship["level"])

        unit["stats"] = stats

        if self._FIXED_CALC_GP:
            unit["gp"] = self._calc_ship_gp(ship, crew)
            stats["gp"] = unit["gp"]

        return unit

    def calc_roster_stats(self, units: Any) -> Any:
        """Calculate stats for all units in a roster-like payload.

        Args:
            units: Either a list of units or a legacy dict keyed by unit id.

        Returns:
            Input object with `stats` and `gp` fields added for each unit.
        """
        self._require_game_data()
        assert self._unit_data is not None
        self._LOGGER.debug("Calculating roster stats")

        if isinstance(units, list):
            ships: list[dict[str, Any]] = []
            crew: dict[str, dict[str, Any]] = {}

            for unit in units:
                def_id = self._get_def_id(unit)
                if not def_id:
                    continue
                meta = self._unit_data.get(def_id)
                if not meta:
                    continue
                if meta["combatType"] == 2:
                    ships.append(unit)
                else:
                    crew[def_id] = unit
                    unit = self.calc_char_stats(unit)

            for ship in ships:
                def_id = self._get_def_id(ship)
                if not def_id:
                    continue
                meta = self._unit_data.get(def_id)
                if not meta:
                    continue
                crw = [crew[cid] for cid in meta["crew"] if cid in crew]
                unit = self.calc_ship_stats(ship, crw)

        elif isinstance(units, dict):
            for unit_id, unit_list in units.items():
                is_char = self._unit_data.get(unit_id, {}).get("combatType") == 1
                if not is_char:
                    continue
                for unit in unit_list:
                    temp_unit = {
                        "defId": unit_id,
                        "rarity": unit.get("currentRarity"),
                        "level": unit.get("currentLevel"),
                        "gear": unit.get("currentTier"),
                        "equipped": [{"equipmentId": gid} for gid in unit.get("gear", [])],
                        "mods": unit.get("equippedStatMod"),
                        "skills": unit.get("skill", []),
                    }
                    temp_unit = self.calc_char_stats(temp_unit)
                    if "stats" in temp_unit:
                        unit["stats"] = temp_unit["stats"]
                    if "gp" in temp_unit:
                        unit["gp"] = temp_unit["gp"]

        return units

    def calc_player_stats(
        self, players: dict[str, Any] | list[dict[str, Any]]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Calculate stats for one or more player payloads.

        Args:
            players: One player object, or a list of player objects, each with a `rosterUnit` element.

        Returns:
            The input object with `stats` and `gp` fields added for each player's roster.

        Raises:
            RuntimeError: If a dict player is missing a 'rosterUnit' key.
            TypeError: If the input object is not a list or dict.
        """
        if not isinstance(players, (list, dict)):
            raise TypeError("Expected a list or dict of players")

        self._require_game_data()
        self._LOGGER.debug("Calculating player stats")

        if isinstance(players, list):
            for player in players:
                self.calc_roster_stats(player.get("rosterUnit"))
            return players
        elif isinstance(players, dict):
            if "rosterUnit" not in players:
                raise RuntimeError("Expected a dict with a 'rosterUnit' key")
            self.calc_roster_stats(players["rosterUnit"])
            return players
        else:
            raise TypeError("Expected a list or dict of players")

    def calc_char_gp(self, char: dict[str, Any]) -> int:
        """Calculate GP for a character.

        Args:
            char: Character object in normalized or raw format.

        Returns:
            Character GP value.
        """
        self._require_game_data()
        return self._calc_char_gp(self._normalize_char(char))

    def calc_ship_gp(self, ship: dict[str, Any], crew: list[dict[str, Any]]) -> int:
        """Calculate GP for a ship.

        Args:
            ship: Ship object in normalized or raw format.
            crew: Crew member list corresponding to the ship.

        Returns:
            Ship GP value.
        """
        self._require_game_data()
        normalized_ship, normalized_crew = self._normalize_ship_and_crew(ship, crew)
        for c in normalized_crew:
            c["gp"] = self._calc_char_gp(c)
        return self._calc_ship_gp(normalized_ship, normalized_crew)

    def _require_game_data(self) -> None:
        if self._unit_data is None:
            raise RuntimeError("set_game_data(game_data) must be called first")

    @classmethod
    def _fetch_game_data_from_github(cls) -> dict[str, Any]:
        try:
            cls._LOGGER.info("Fetching game data from %s", cls._DEFAULT_GAMEDATA_URL)
            with urllib.request.urlopen(cls._DEFAULT_GAMEDATA_URL, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # pragma: no cover - network failure path
            cls._LOGGER.exception("Failed to fetch game data from GitHub")
            raise RuntimeError(f"Unable to retrieve game data from {cls._DEFAULT_GAMEDATA_URL}") from exc

        return cls._normalize_game_data_payload(payload)

    @staticmethod
    def _normalize_game_data_payload(payload: dict[str, Any]) -> dict[str, Any]:
        if "unitData" in payload:
            return payload
        data = payload.get("data")
        if isinstance(data, dict) and "unitData" in data:
            return data
        StatCalc._LOGGER.error("Unsupported game data payload format")
        raise RuntimeError("Unsupported game data payload format")

    def _get_def_id(self, unit: dict[str, Any] | None) -> str | None:
        if not unit:
            return None
        if unit.get("defId"):
            result: str = str(unit["defId"])
            return result
        definition_id = unit.get("definitionId")
        if definition_id:
            result = str(definition_id).split(":")[0]
            return result
        return None

    @staticmethod
    def _table_get(table: Any, key: Any, default: Any = 0) -> Any:
        if table is None:
            return default
        if isinstance(table, list):
            try:
                idx = int(key)
            except (TypeError, ValueError):
                return default
            if 0 <= idx < len(table):
                return table[idx]
            return default
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

    @staticmethod
    def _add_stat(stats: dict[str, Any], stat_id: Any, value: float) -> None:
        key = str(stat_id)
        stats[key] = stats.get(key, 0) + value

    def _normalize_char(self, char: dict[str, Any]) -> dict[str, Any]:
        if not char.get("defId"):
            normalized = {
                "defId": char["definitionId"].split(":")[0],
                "rarity": char["currentRarity"],
                "level": char["currentLevel"],
                "gear": char["currentTier"],
                "equipped": char.get("equipment", []),
                "equippedStatMod": char.get("equippedStatMod"),
                "relic": char.get("relic"),
                "skills": [{"id": skill["id"], "tier": skill["tier"] + 2} for skill in char.get("skill", [])],
            }
        else:
            normalized = copy.deepcopy(char)

        normalized.setdefault("equipped", [])
        normalized.setdefault("skills", [])
        normalized.setdefault("mods", None)
        normalized.setdefault("equippedStatMod", None)
        return normalized

    def _normalize_ship_and_crew(
        self, ship: dict[str, Any], crew: list[dict[str, Any]]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        if not ship.get("defId"):
            normalized_ship = {
                "defId": ship["definitionId"].split(":")[0],
                "rarity": ship["currentRarity"],
                "level": ship["currentLevel"],
                "skills": [{"id": skill["id"], "tier": skill["tier"] + 2} for skill in ship.get("skill", [])],
            }
            normalized_crew = []
            for c in crew:
                normalized_crew.append(
                    {
                        "defId": c["definitionId"].split(":")[0],
                        "rarity": c["currentRarity"],
                        "level": c["currentLevel"],
                        "gear": c["currentTier"],
                        "equipped": c.get("equipment", []),
                        "equippedStatMod": c.get("equippedStatMod"),
                        "mods": c.get("mods"),
                        "relic": c.get("relic"),
                        "skills": [{"id": s["id"], "tier": s["tier"] + 2} for s in c.get("skill", [])],
                        "gp": c.get("gp"),
                    }
                )
            return normalized_ship, normalized_crew

        normalized_ship = copy.deepcopy(ship)
        normalized_ship.setdefault("skills", [])
        normalized_crew = [copy.deepcopy(c) for c in crew]
        for c in normalized_crew:
            c.setdefault("skills", [])
            c.setdefault("equipped", [])
            c.setdefault("mods", None)
            c.setdefault("equippedStatMod", None)
        return normalized_ship, normalized_crew

    def _get_char_raw_stats(self, char: dict[str, Any]) -> dict[str, Any]:
        assert self._unit_data is not None
        assert self._gear_data is not None
        assert self._relic_data is not None
        def_id = char["defId"]
        meta = self._unit_data.get(def_id)
        if meta is None:
            raise KeyError(
                f"Unit '{def_id}' not found in game data. "
                f"The unit may be non-obtainable or missing from the data build."
            )
        gear_lvl = self._table_get(meta["gearLvl"], char["gear"], {})
        stats = {
            "base": dict(gear_lvl.get("stats", {})),
            "growthModifiers": dict(self._table_get(meta["growthModifiers"], char["rarity"], {})),
            "gear": {},
        }

        base = stats["base"]
        gear_agg = stats["gear"]

        for gear_piece in char.get("equipped", []):
            gear_id = gear_piece.get("equipmentId") if isinstance(gear_piece, dict) else gear_piece
            gear_id_str = str(gear_id)
            gear_entry = self._gear_data.get(gear_id_str) or self._gear_data.get(gear_id_str)
            if not gear_entry:
                continue
            for stat_id, value in gear_entry.get("stats", {}).items():
                if str(stat_id) in {"2", "3", "4"}:
                    self._add_stat(base, stat_id, value)
                else:
                    self._add_stat(gear_agg, stat_id, value)

        relic = char.get("relic")
        if relic and relic.get("currentTier", 0) > 2:
            relic_def = self._table_get(meta.get("relic", []), relic["currentTier"], None)
            if relic_def:
                relic_def_str = str(relic_def)
                relic_entry = self._relic_data.get(relic_def_str) or self._relic_data.get(relic_def_str)
                if relic_entry:
                    for stat_id, value in relic_entry.get("stats", {}).items():
                        self._add_stat(base, stat_id, value)
                    for stat_id, value in relic_entry.get("gms", {}).items():
                        self._add_stat(stats["growthModifiers"], stat_id, value)

        return stats

    def _get_ship_raw_stats(self, ship: dict[str, Any], crew: list[dict[str, Any]]) -> dict[str, Any]:
        assert self._unit_data is not None
        assert self._cr_tables is not None
        def_id = ship["defId"]
        meta = self._unit_data.get(def_id)
        if meta is None:
            raise KeyError(
                f"Ship '{def_id}' not found in game data. "
                f"The unit may be non-obtainable or missing from the data build."
            )

        if len(crew) != len(meta["crew"]):
            raise ValueError(f"Incorrect number of crew members for ship {ship['defId']}")

        for char in crew:
            if char["defId"] not in meta["crew"]:
                raise ValueError(f"Unit {char['defId']} is not in {ship['defId']}'s crew")

        crew_rating = self._get_crewless_crew_rating(ship) if len(crew) == 0 else self._get_crew_rating(crew)

        stats = {
            "base": dict(meta.get("stats", {})),
            "crew": {},
            "growthModifiers": dict(self._table_get(meta["growthModifiers"], ship["rarity"], {})),
        }

        stat_multiplier = self._table_get(self._cr_tables["shipRarityFactor"], ship["rarity"]) * crew_rating
        for stat_id, stat_value in meta.get("crewStats", {}).items():
            sid = int(stat_id)
            precision = 8 if (sid < 16 or sid == 28) else 0
            stats["crew"][str(stat_id)] = self._floor(stat_value * stat_multiplier, precision)

        return stats

    def _get_crew_rating(self, crew: list[dict[str, Any]]) -> float:
        assert self._cr_tables is not None
        total_cr: float = 0
        for char in crew:
            total_cr += self._table_get(self._cr_tables["unitLevelCR"], char["level"])
            total_cr += self._table_get(self._cr_tables["crewRarityCR"], char["rarity"])
            total_cr += self._table_get(self._cr_tables["gearLevelCR"], char["gear"])

            piece_cr = self._table_get(self._cr_tables["gearPieceCR"], char["gear"])
            total_cr += piece_cr * len(char.get("equipped", []))

            for skill in char.get("skills", []):
                total_cr += self._get_skill_crew_rating(skill)

            if char.get("mods"):
                for mod in char["mods"]:
                    total_cr += self._table_get(
                        self._table_get(self._cr_tables["modRarityLevelCR"], mod["pips"]),
                        mod["level"],
                    )
            elif char.get("equippedStatMod"):
                for mod in char["equippedStatMod"]:
                    total_cr += self._table_get(
                        self._table_get(
                            self._cr_tables["modRarityLevelCR"],
                            int(mod["definitionId"][1]),
                        ),
                        mod["level"],
                    )

            relic = char.get("relic")
            if relic and relic.get("currentTier", 0) > 2:
                tier = relic["currentTier"]
                total_cr += self._table_get(self._cr_tables["relicTierCR"], tier)
                total_cr += char["level"] * self._table_get(self._cr_tables["relicTierLevelFactor"], tier)

        return total_cr

    def _get_skill_crew_rating(self, skill: dict[str, Any]) -> float:
        assert self._cr_tables is not None
        value: float = self._table_get(self._cr_tables["abilityLevelCR"], skill["tier"])
        return value

    def _get_crewless_crew_rating(self, ship: dict[str, Any]) -> float:
        assert self._cr_tables is not None
        return self._floor(
            self._table_get(self._cr_tables["crewRarityCR"], ship["rarity"])
            + 3.5 * self._table_get(self._cr_tables["unitLevelCR"], ship["level"])
            + self._get_crewless_skills_crew_rating(ship.get("skills", []))
        )

    def _get_crewless_skills_crew_rating(self, skills: list[dict[str, Any]]) -> float:
        assert self._cr_tables is not None
        cr = 0.0
        for skill in skills:
            mult = 0.696 if str(skill["id"]).startswith("hardware") else 2.46
            cr += mult * self._table_get(self._cr_tables["abilityLevelCR"], skill["tier"])
        return cr

    def _calculate_base_stats(self, stats: dict[str, Any], level: int, base_id: str) -> dict[str, Any]:
        assert self._unit_data is not None
        assert self._cr_tables is not None
        base = stats["base"]
        gms = stats["growthModifiers"]

        self._add_stat(base, 2, self._floor(self._table_get(gms, 2) * level, 8))
        self._add_stat(base, 3, self._floor(self._table_get(gms, 3) * level, 8))
        self._add_stat(base, 4, self._floor(self._table_get(gms, 4) * level, 8))

        ud = self._unit_data[base_id]

        if self._table_get(base, 61):
            mms = self._cr_tables.get(ud["masteryModifierID"], {})
            for stat_id, value in mms.items():
                self._add_stat(base, stat_id, self._table_get(base, 61) * value)

        self._add_stat(base, 1, self._table_get(base, 2) * 18)
        self._add_stat(
            base,
            6,
            self._floor(
                self._table_get(base, 6) + (self._table_get(base, ud["primaryStat"]) * 1.4),
                8,
            )
            - self._table_get(base, 6),
        )
        self._add_stat(
            base,
            7,
            self._floor(self._table_get(base, 7) + (self._table_get(base, 4) * 2.4), 8) - self._table_get(base, 7),
        )
        self._add_stat(
            base,
            8,
            self._floor(
                self._table_get(base, 8) + (self._table_get(base, 2) * 0.14) + (self._table_get(base, 3) * 0.07),
                8,
            )
            - self._table_get(base, 8),
        )
        self._add_stat(
            base,
            9,
            self._floor(self._table_get(base, 9) + (self._table_get(base, 4) * 0.1), 8) - self._table_get(base, 9),
        )
        self._add_stat(
            base,
            14,
            self._floor(self._table_get(base, 14) + (self._table_get(base, 3) * 0.4), 8) - self._table_get(base, 14),
        )

        self._add_stat(base, 12, 24 * 1e8)
        self._add_stat(base, 13, 24 * 1e8)
        self._add_stat(base, 15, 0)
        self._add_stat(base, 16, 150 * 1e6)
        self._add_stat(base, 18, 15 * 1e6)

        return stats

    def _calculate_mod_stats(self, base_stats: dict[str, Any], char: dict[str, Any]) -> dict[str, Any]:
        # Mod definitionId is a 3 digit number, where the first digit is the set id,
        # the second digit is the rarity (pips/dots) and the third digit is the slot (1-6)
        # slot = {1: "Square", 2: "Arrow", 3: "Diamond", 4: "Triangle", 5: "Circle", 6: "Plus/Cross"}
        if not char.get("mods") and not char.get("equippedStatMod"):
            return {}

        set_bonuses: dict[int, dict[str, int]] = {}
        raw_mod_stats: dict[str, float] = {}

        if char.get("mods"):
            for mod in char["mods"]:
                if not mod.get("set"):
                    continue

                set_id = int(mod["set"])
                if set_id in set_bonuses:
                    set_bonuses[set_id]["count"] += 1
                    if mod.get("level") == 15:
                        set_bonuses[set_id]["maxLevel"] += 1
                else:
                    set_bonuses[set_id] = {
                        "count": 1,
                        "maxLevel": 1 if mod.get("level") == 15 else 0,
                    }

                if mod.get("stat"):
                    for stat in mod["stat"]:
                        sid, sval = stat
                        key = str(sid)
                        raw_mod_stats[key] = raw_mod_stats.get(key, 0) + self._scale_mod_stat_value(sid, sval)
                else:
                    stat = mod.get("primaryStat")
                    secondary = mod.get("secondaryStat", [])
                    i = 0
                    while stat:
                        sid = stat["unitStat"]
                        key = str(sid)
                        raw_mod_stats[key] = raw_mod_stats.get(key, 0) + self._scale_mod_stat_value(sid, stat["value"])
                        if i >= len(secondary):
                            break
                        stat = secondary[i]
                        i += 1

        elif char.get("equippedStatMod"):
            for mod in char["equippedStatMod"]:
                set_id = int(mod["definitionId"][0])
                if set_id in set_bonuses:
                    set_bonuses[set_id]["count"] += 1
                    if mod.get("level") == 15:
                        set_bonuses[set_id]["maxLevel"] += 1
                else:
                    set_bonuses[set_id] = {
                        "count": 1,
                        "maxLevel": 1 if mod.get("level") == 15 else 0,
                    }

                stat = mod.get("primaryStat", {}).get("stat")
                secondary = mod.get("secondaryStat", [])
                i = 0
                while stat:
                    sid = stat["unitStatId"]
                    key = str(sid)
                    raw_mod_stats[key] = raw_mod_stats.get(key, 0) + float(stat["unscaledDecimalValue"])
                    if i >= len(secondary):
                        break
                    stat = secondary[i].get("stat")
                    i += 1

        for set_id, bonus in set_bonuses.items():
            set_def = self._table_get(self._mod_set_data, set_id, None)
            if not set_def:
                continue
            multiplier = (bonus["count"] // set_def["count"]) + (bonus["maxLevel"] // set_def["count"])
            key = str(set_def["id"])
            raw_mod_stats[key] = raw_mod_stats.get(key, 0) + (set_def["value"] * multiplier)

        mod_stats: dict[str, float] = {}
        for stat_id_str, value in raw_mod_stats.items():
            stat_id = int(stat_id_str)
            if stat_id == 41:
                self._add_stat(mod_stats, 6, value)
                self._add_stat(mod_stats, 7, value)
            elif stat_id == 42:
                self._add_stat(mod_stats, 8, value)
                self._add_stat(mod_stats, 9, value)
            elif stat_id == 48:
                self._add_stat(
                    mod_stats,
                    6,
                    self._floor(
                        self._table_get(mod_stats, 6) + (self._table_get(base_stats, 6) * 1e-8 * value),
                        8,
                    )
                    - self._table_get(mod_stats, 6),
                )
                self._add_stat(
                    mod_stats,
                    7,
                    self._floor(
                        self._table_get(mod_stats, 7) + (self._table_get(base_stats, 7) * 1e-8 * value),
                        8,
                    )
                    - self._table_get(mod_stats, 7),
                )
            elif stat_id == 49:
                self._add_stat(
                    mod_stats,
                    8,
                    self._floor(
                        self._table_get(mod_stats, 8) + (self._table_get(base_stats, 8) * 1e-8 * value),
                        8,
                    )
                    - self._table_get(mod_stats, 8),
                )
                self._add_stat(
                    mod_stats,
                    9,
                    self._floor(
                        self._table_get(mod_stats, 9) + (self._table_get(base_stats, 9) * 1e-8 * value),
                        8,
                    )
                    - self._table_get(mod_stats, 9),
                )
            elif stat_id == 53:
                self._add_stat(mod_stats, 21, value)
                self._add_stat(mod_stats, 22, value)
            elif stat_id == 54:
                self._add_stat(mod_stats, 35, value)
                self._add_stat(mod_stats, 36, value)
            elif stat_id == 55:
                self._add_stat(
                    mod_stats,
                    1,
                    self._floor(
                        self._table_get(mod_stats, 1) + (self._table_get(base_stats, 1) * 1e-8 * value),
                        8,
                    )
                    - self._table_get(mod_stats, 1),
                )
            elif stat_id == 56:
                self._add_stat(
                    mod_stats,
                    28,
                    self._floor(
                        self._table_get(mod_stats, 28) + (self._table_get(base_stats, 28) * 1e-8 * value),
                        8,
                    )
                    - self._table_get(mod_stats, 28),
                )
            elif stat_id == 57:
                self._add_stat(
                    mod_stats,
                    5,
                    self._floor(
                        self._table_get(mod_stats, 5) + (self._table_get(base_stats, 5) * 1e-8 * value),
                        8,
                    )
                    - self._table_get(mod_stats, 5),
                )
            else:
                self._add_stat(mod_stats, stat_id_str, value)

        return mod_stats

    @staticmethod
    def _scale_mod_stat_value(stat_id: int, value: float) -> float:
        if int(stat_id) in {1, 5, 28, 41, 42}:
            return value * 1e8
        return value * 1e6

    def _format_stats(self, stats: dict[str, Any], level: int) -> dict[str, Any]:
        scale = 1e-8

        if stats.get("mods"):
            for stat_id in list(stats["mods"].keys()):
                stats["mods"][stat_id] = round(stats["mods"][stat_id])

        if scale != 1:
            for stat_id in list(stats["base"].keys()):
                stats["base"][stat_id] *= scale
            for stat_id in list(stats.get("gear", {}).keys()):
                stats["gear"][stat_id] *= scale
            for stat_id in list(stats.get("crew", {}).keys()):
                stats["crew"][stat_id] *= scale
            for stat_id in list(stats["growthModifiers"].keys()):
                stats["growthModifiers"][stat_id] *= scale
            if stats.get("mods"):
                for stat_id in list(stats["mods"].keys()):
                    stats["mods"][stat_id] *= scale

        if self._FIXED_PERCENT_VALS or self._FIXED_GAME_STYLE:
            self._convert_percent(
                stats,
                14,
                lambda val: self._convert_flat_crit_to_percent(val, scale * 1e8),
                level,
            )
            self._convert_percent(
                stats,
                15,
                lambda val: self._convert_flat_crit_to_percent(val, scale * 1e8),
                level,
            )
            self._convert_percent(
                stats,
                8,
                lambda val: self._convert_flat_def_to_percent(val, level, scale * 1e8, "crew" in stats),
                level,
            )
            self._convert_percent(
                stats,
                9,
                lambda val: self._convert_flat_def_to_percent(val, level, scale * 1e8, "crew" in stats),
                level,
            )
            self._convert_percent(
                stats,
                37,
                lambda val: self._convert_flat_acc_to_percent(val, scale * 1e8),
                level,
            )
            self._convert_percent(
                stats,
                38,
                lambda val: self._convert_flat_acc_to_percent(val, scale * 1e8),
                level,
            )
            self._convert_percent(
                stats,
                12,
                lambda val: self._convert_flat_acc_to_percent(val, scale * 1e8),
                level,
            )
            self._convert_percent(
                stats,
                13,
                lambda val: self._convert_flat_acc_to_percent(val, scale * 1e8),
                level,
            )
            self._convert_percent(
                stats,
                39,
                lambda val: self._convert_flat_crit_avoid_to_percent(val, scale * 1e8),
                level,
            )
            self._convert_percent(
                stats,
                40,
                lambda val: self._convert_flat_crit_avoid_to_percent(val, scale * 1e8),
                level,
            )

        if self._FIXED_GAME_STYLE:
            gs_stats: dict[str, Any] = {"final": {}}

            stat_list = list(stats["base"].keys())

            def add_stat_id(sid: str) -> None:
                if sid not in stat_list:
                    stat_list.append(sid)

            if "gear" in stats:
                for sid in stats["gear"].keys():
                    add_stat_id(sid)
                if "mods" in stats:
                    for sid in stats["mods"].keys():
                        add_stat_id(sid)
                    gs_stats["mods"] = stats["mods"]

                for stat_id in stat_list:
                    stat_int = int(stat_id)
                    flat_stat_id = stat_int
                    if stat_int in {21, 22}:
                        flat_stat_id = stat_int - 7
                    elif stat_int in {35, 36}:
                        flat_stat_id = stat_int + 4

                    key = str(flat_stat_id)
                    gs_stats["final"][key] = gs_stats["final"].get(key, 0) + (
                        self._table_get(stats["base"], stat_id)
                        + self._table_get(stats["gear"], stat_id)
                        + (self._table_get(stats["mods"], stat_id) if "mods" in stats else 0)
                    )
            else:
                for sid in stats.get("crew", {}).keys():
                    add_stat_id(sid)
                gs_stats["crew"] = stats.get("crew", {})

                for stat_id in stat_list:
                    gs_stats["final"][str(stat_id)] = self._table_get(stats["base"], stat_id) + self._table_get(
                        stats["crew"], stat_id
                    )

            stats = gs_stats

        return stats

    def _rename_stats(self, stats: dict[str, Any], lang: str = "eng_us") -> dict[str, Any]:
        rn_stats = {}
        for stat_type, stat_values in stats.items():
            if not isinstance(stat_values, dict):
                rn_stats[stat_type] = stat_values
                continue
            rn_stats[stat_type] = {}
            for stat_id, value in stat_values.items():
                stat_name = self.STATS_NAME_MAP.get(stat_id, {}).get("name", stat_id)
                rn_stats[stat_type][stat_name] = value
        self._LOGGER.debug("Done renaming stats")
        return rn_stats

    def _convert_percent(
        self,
        stats: dict[str, Any],
        stat_id: int,
        convert_func: Any,
        level: int,
    ) -> None:
        del level
        sid = str(stat_id)
        flat = self._table_get(stats["base"], sid)
        percent = convert_func(flat)
        stats["base"][sid] = percent
        last = percent

        if "crew" in stats:
            if self._table_get(stats["crew"], sid):
                flat = flat + self._table_get(stats["crew"], sid)
                stats["crew"][sid] = convert_func(flat) - last
        else:
            if "gear" in stats and self._table_get(stats["gear"], sid):
                flat = flat + self._table_get(stats["gear"], sid)
                percent = convert_func(flat)
                stats["gear"][sid] = percent - last
                last = percent
            if "mods" in stats and self._table_get(stats["mods"], sid):
                flat = flat + self._table_get(stats["mods"], sid)
                stats["mods"][sid] = convert_func(flat) - last

    def _calc_char_gp(self, char: dict[str, Any]) -> int:
        assert self._gp_tables is not None
        gp = self._table_get(self._gp_tables["unitLevelGP"], char["level"])
        gp += self._table_get(self._gp_tables["unitRarityGP"], char["rarity"])
        gp += self._table_get(self._gp_tables["gearLevelGP"], char["gear"])

        for piece in char.get("equipped", []):
            slot = piece.get("slot") if isinstance(piece, dict) else None
            gp += self._table_get(
                self._table_get(self._gp_tables["gearPieceGP"], char["gear"]),
                slot,
            )

        for skill in char.get("skills", []):
            gp += self._get_skill_gp(char["defId"], skill)

        if char.get("purchasedAbilityId"):
            gp += len(char["purchasedAbilityId"]) * self._table_get(self._gp_tables["abilitySpecialGP"], "ultimate")

        if char.get("mods"):
            for mod in char["mods"]:
                gp += self._table_get(
                    self._table_get(
                        self._table_get(
                            self._gp_tables["modRarityLevelTierGP"],
                            mod["pips"],
                        ),
                        mod["level"],
                    ),
                    mod["tier"],
                )
        elif char.get("equippedStatMod"):
            for mod in char["equippedStatMod"]:
                gp += self._table_get(
                    self._table_get(
                        self._table_get(
                            self._gp_tables["modRarityLevelTierGP"],
                            int(mod["definitionId"][1]),
                        ),
                        mod["level"],
                    ),
                    mod["tier"],
                )

        relic = char.get("relic")
        if relic and relic.get("currentTier", 0) > 2:
            tier = relic["currentTier"]
            gp += self._table_get(self._gp_tables["relicTierGP"], tier)
            gp += char["level"] * self._table_get(self._gp_tables["relicTierLevelFactor"], tier)

        return int(self._floor(gp * 1.5))

    def _get_skill_gp(self, unit_id: str, skill: dict[str, Any]) -> float:
        assert self._unit_data is not None
        assert self._gp_tables is not None
        skill_def = next(
            (s for s in self._unit_data[unit_id]["skills"] if s["id"] == skill["id"]),
            None,
        )
        if not skill_def:
            return 0
        power_override = self._table_get(skill_def.get("powerOverrideTags", {}), skill["tier"], None)
        if power_override:
            gp_value: float = self._table_get(self._gp_tables["abilitySpecialGP"], power_override)
            return gp_value
        gp_value = self._table_get(self._gp_tables["abilityLevelGP"], skill["tier"], 0)
        return gp_value

    def _calc_ship_gp(self, ship: dict[str, Any], crew: list[dict[str, Any]] | None = None) -> int:
        assert self._unit_data is not None
        assert self._gp_tables is not None
        if crew is None:
            crew = []

        expected = self._unit_data[ship["defId"]]["crew"]
        if len(crew) != len(expected):
            raise ValueError(f"Incorrect number of crew members for ship {ship['defId']}")

        for char in crew:
            if char["defId"] not in expected:
                raise ValueError(f"Unit {char['defId']} is not in {ship['defId']}'s crew")

        if len(crew) == 0:
            gps = self._get_crewless_skills_gp(ship["defId"], ship.get("skills", []))
            gps["level"] = self._table_get(self._gp_tables["unitLevelGP"], ship["level"])
            gp = (gps["level"] * 3.5 + gps["ability"] * 5.74 + gps["reinforcement"] * 1.61) * self._table_get(
                self._gp_tables["shipRarityFactor"], ship["rarity"]
            )
            gp += gps["level"] + gps["ability"] + gps["reinforcement"]
        else:
            gp = sum(c["gp"] for c in crew)
            gp *= self._table_get(self._gp_tables["shipRarityFactor"], ship["rarity"]) * self._table_get(
                self._gp_tables["crewSizeFactor"], len(crew)
            )
            gp += self._table_get(self._gp_tables["unitLevelGP"], ship["level"])
            for skill in ship.get("skills", []):
                gp += self._get_skill_gp(ship["defId"], skill)

        return int(self._floor(gp * 1.5))

    def _get_crewless_skills_gp(self, unit_id: str, skills: list[dict[str, Any]]) -> dict[str, float]:
        assert self._unit_data is not None
        assert self._gp_tables is not None
        ability = 0.0
        reinforcement = 0.0

        for skill in skills:
            skill_def = next(
                (s for s in self._unit_data[unit_id]["skills"] if s["id"] == skill["id"]),
                None,
            )
            if not skill_def:
                continue
            o_tag = self._table_get(skill_def.get("powerOverrideTags", {}), skill["tier"], None)
            if o_tag and str(o_tag).startswith("reinforcement"):
                reinforcement += self._table_get(self._gp_tables["abilitySpecialGP"], o_tag)
            else:
                ability += (
                    self._table_get(self._gp_tables["abilitySpecialGP"], o_tag)
                    if o_tag
                    else self._table_get(self._gp_tables["abilityLevelGP"], skill["tier"])
                )

        return {"ability": ability, "reinforcement": reinforcement}

    @staticmethod
    def _floor(value: float, digits: int = 0) -> float:
        factor = 10**digits
        result: float = math.floor(value / factor) * factor
        return result

    @staticmethod
    def _convert_flat_def_to_percent(
        value: float,
        level: int = 85,
        scale: float = 1,
        is_ship: bool = False,
    ) -> float:
        val = value / scale
        level_effect = 300 + level * 5 if is_ship else level * 7.5
        return (val / (level_effect + val)) * scale

    @staticmethod
    def _convert_flat_crit_to_percent(value: float, scale: float = 1) -> float:
        val = value / scale
        return (val / 2400 + 0.1) * scale

    @staticmethod
    def _convert_flat_acc_to_percent(value: float, scale: float = 1) -> float:
        val = value / scale
        return (val / 1200) * scale

    @staticmethod
    def _convert_flat_crit_avoid_to_percent(value: float, scale: float = 1) -> float:
        val = value / scale
        return (val / 2400) * scale
