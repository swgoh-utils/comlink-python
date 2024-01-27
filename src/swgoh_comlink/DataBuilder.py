"""
Python library module for building data files that can be used by the StatCalc module in the swgoh_comlink package.
"""

import base64
import io
import json
import logging
import os
import re
import shutil
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swgoh_comlink import Utils
from swgoh_comlink.SwgohComlink import SwgohComlink

_COMMENT_START = '#'
_FIELD_SEPARATOR = '|'
_NEWLINE_CHARACTER = '\n'
_PRE_PATTERN = re.compile(r'^\[[0-9A-F]*?]')
_POST_PATTERN = re.compile(r'\s+\(([A-Z]+)\)\[-]$')

logger = Utils.get_logger(name='DataBuilder')


class DataBuilderException(Exception):
    pass


class DataBuilderRuntimeError(RuntimeError):
    pass


def _verify_data_path(data_path: str or Path):
    """Validate data path and recursively create if not found"""
    finished = False
    target_path = Path(data_path)
    parents = list(target_path.parents)
    parents.insert(0, target_path)
    index = 0
    while finished is False:
        logger.info(f"Checking {parents[index]}...")
        try:
            os.mkdir(parents[index])
            if index != 0:
                index -= 1
            else:
                finished = True
        except FileExistsError:
            logger.info(f"{data_path} exists.")
            finished = True
        except FileNotFoundError as path_err_str:
            index += 1
            target_path = parents[index]
            logger.debug(f"{path_err_str}")
            logger.info(f"A parent folder in {data_path} does not exist. Moving up one level to {target_path}.")


def _write_json_file(data_path: str, file_name: str, json_data: dict) -> None:
    """Method to write file contents to disk"""

    logger.info(f"File write args received: {data_path=}, {file_name=}")
    if not file_name.endswith('.json'):
        file_name += '.json'
    full_path = os.path.join(data_path, file_name)
    if os.path.isfile(full_path):
        file_name_bak = file_name + '-' + time.strftime("%Y%m%d_%H%M%S", time.localtime()) + '.bak'
        logger.info(f"{file_name} already exists. Renaming to {file_name_bak} before saving.")
        _verify_data_path(os.path.join(data_path, 'backups'))
        full_name_bak = os.path.join(data_path, 'backups', file_name_bak)
        shutil.move(full_path, full_name_bak)
    try:
        logger.info(f"Opening {full_path}...")
        with open(full_path, 'w') as fn:
            json.dump(json_data, fn, indent=2, ensure_ascii=False, sort_keys=True)
    except Exception as e_str:
        logger.error(f"Exception caught: {e_str}")
        raise e_str
    logger.info(f"{file_name} written successfully.")
    return


def _read_json_file(data_path: str, file_name: str) -> dict:
    """Retrieve JSON data from file and return dictionary"""

    if not file_name.endswith('.json'):
        file_name += '.json'
    logger.info(f"Reading contents of {file_name}")
    full_path = os.path.join(data_path, file_name)
    try:
        with open(full_path) as fn:
            contents = json.load(fn)
    except FileNotFoundError:
        logger.error(f'File {full_path} was not found. Please check that it exists.')
        raise f'File {full_path} was not found. Please check that it exists.'
    except Exception as e_str:
        logger.error(f'Encountered {e_str} while attempting to read contents of {full_path}')
        raise e_str
    else:
        logger.info(f'Returning contents of {full_path} ({len(contents)} bytes).')
        return contents


def _load_stat_enums_map_dict() -> tuple[dict, dict]:
    """Load statsEnum mapping data from JSON file"""

    logger.info(f"Creating 'stats_enum' and 'localization_map' objects")
    stat_enums = {}
    localization_map = {}
    for key, value in Utils.UNIT_STAT_ENUMS_MAP.items():
        if 'tableKey' in value.keys():
            stat_enums[value['tableKey']] = key
        if 'nameKey' in value.keys():
            localization_map[value['nameKey']] = key
    return stat_enums, localization_map


def _is_comment_or_invalid(loc_line: str) -> bool:
    return loc_line.startswith(_COMMENT_START) or _FIELD_SEPARATOR not in loc_line


def _apply_value_patterns(value: str) -> str:
    value = _PRE_PATTERN.sub('', value)
    value = _POST_PATTERN.sub('', value)
    return '' if value is None else value


def _compare_game_data_versions(current_version: dict, server_version: dict) -> bool:
    stripped_current_version = {"game": current_version['game'], "language": current_version['language']}
    if stripped_current_version == server_version:
        return True
    else:
        return False


@dataclass
class DataBuilder:
    """Base container class representing a collection of methods for managing game data files populated with information
    retrieved from the game servers directly. This class is not intended to be instantiated.

    """
    _INITIALIZED = False
    _VERSION = {
        "game": "",
        "language": "",
        "languages": []
    }

    _STATS_ENUM = Utils.STAT_ENUMS
    _GAME_DATA = {}
    _ZIP_GAME_DATA = False
    _USE_SEGMENTS = False
    _USE_UNZIP = False
    _LOCALIZATION_MAP = {}

    _DATA_PATH = os.path.join(os.getcwd(), 'data')
    _DATA_FILE_PATHS = [
        _DATA_PATH,
        os.path.join(_DATA_PATH, 'game'),
        os.path.join(_DATA_PATH, 'game', 'backups'),
        os.path.join(_DATA_PATH, 'units'),
        os.path.join(_DATA_PATH, 'units', 'backups'),
        os.path.join(_DATA_PATH, 'languages'),
        os.path.join(_DATA_PATH, 'languages', 'backups')
    ]
    _DATA_VERSION_FILE = 'dataVersion'
    _GAME_DATA_PATH_SUB_FOLDER = 'game'
    _GAME_DATA_FILE = 'gameData'
    _GAME_DATA_FILES = [
        'crTables',
        'gearData',
        'gpTables',
        'modSetData',
        'relicData',
        'unitData'
    ]
    _STATS_ENUM_MAP_LOADED = False
    _LOG_LEVEL = 'INFO'
    _LANGUAGE_FILE_SKIP_LIST = ['key_mapping']
    _COMLINK = SwgohComlink()
    _AUTO_UPDATE_GAME_DATA = False
    _AUTO_UPDATE_GAME_DATA_INTERVAL_DEFAULT = 60  # 5 minutes
    _AUTO_UPDATE_GAME_DATA_INTERVAL_MIN = 30  # 5 minutes
    _AUTO_UPDATE_GAME_DATA_INTERVAL = _AUTO_UPDATE_GAME_DATA_INTERVAL_DEFAULT
    _AUTO_UPDATE_GAME_DATA_THREAD_NAME = None
    _AUTO_UPDATE_GAME_DATA_THREAD_ID = None

    @classmethod
    def get_language_file_path(cls) -> str:
        """Return path to localized language files"""
        return os.path.join(cls._DATA_PATH, 'languages')

    @classmethod
    def _auto_update_game_data(cls) -> None:
        """
        Background process to automatically update game data files from the servers if a new version is detected
        """
        if cls._AUTO_UPDATE_GAME_DATA_INTERVAL < cls._AUTO_UPDATE_GAME_DATA_INTERVAL_MIN:
            logger.warning(f"Setting the interval for automatic game data update checks to less than " +
                           f"{cls._AUTO_UPDATE_GAME_DATA_INTERVAL_MIN} is not recommended. It may cause your Comlink " +
                           "process to become rate limited by Capital Games.")
        thread_name = threading.current_thread().name
        sleep_minutes = cls._AUTO_UPDATE_GAME_DATA_INTERVAL * 60
        logger.info(f"Automatic game data update thread [{thread_name}] starting with an update interval of " +
                    f"{cls._AUTO_UPDATE_GAME_DATA_INTERVAL}")
        thread_shutdown = False
        while thread_shutdown is False:
            auto_update_polling_counter = 0
            server_game_versions = cls._COMLINK.get_latest_game_data_version()
            if not _compare_game_data_versions(server_game_versions, cls._VERSION):
                logger.info(
                    f"Server game versions {server_game_versions} does not equal the current data version file.")
                cls.update_game_data()
                cls.update_localization_bundle()

                logger.info("Writing game version information to disk...")
                _write_json_file(cls._DATA_PATH, cls._DATA_VERSION_FILE, cls._VERSION)
            while thread_shutdown is False and auto_update_polling_counter < sleep_minutes:
                if cls._AUTO_UPDATE_GAME_DATA is False:
                    logger.info(f"Automatic game data updates have been disabled. " +
                                f"Shutting down thread {thread_name}.")
                    thread_shutdown = True
                time.sleep(10)
                auto_update_polling_counter += 10
            time.sleep(sleep_minutes)
        cls._AUTO_UPDATE_GAME_DATA_THREAD_NAME = None
        logger.info(f"Thread {thread_name} stopped.")

    @classmethod
    def _start_auto_update_thread(cls) -> bool:
        thread_name = "AUTO UPDATE GAME DATA THREAD"
        logger.info(f"Starting auto update thread [{thread_name}]...")
        update_t = threading.Thread(target=cls._auto_update_game_data,
                                    name=thread_name,
                                    daemon=True)
        update_t.start()
        status = update_t.is_alive()
        if status is True:
            cls._AUTO_UPDATE_GAME_DATA_THREAD_NAME = thread_name
        return status

    @classmethod
    def _process_localization_line_unit_name(cls, loc_line: str) -> tuple or None:
        if _is_comment_or_invalid(loc_line):
            return

        loc_line = loc_line.rstrip(_NEWLINE_CHARACTER)
        name_key, name_desc = loc_line.split(_FIELD_SEPARATOR)

        if not name_key or not name_desc:
            return

        if not (name_key.startswith('UNIT_') and name_key.endswith('_NAME')):
            return

        name_desc = _apply_value_patterns(name_desc)
        return name_key, name_desc

    @classmethod
    def _process_localization_line_stat_ids(cls, loc_line: str):
        if _is_comment_or_invalid(loc_line):
            return

        loc_line = loc_line.rstrip(_NEWLINE_CHARACTER)
        key, value = loc_line.split(_FIELD_SEPARATOR)
        logger.debug(f"{key=} {value=}")

        if not key or not value:
            return

        if key not in cls._LOCALIZATION_MAP.keys():
            return

        value = _apply_value_patterns(value)

        logger.debug(f"Returning {key=} {value=}")
        return key, value

    @classmethod
    def _process_file_contents_by_line(cls, content: list) -> tuple[dict, dict]:
        """Iterate through file contents list and create language map from information contained within"""
        logger.info(f"Processing language content...")
        lang_map = {}
        unit_name_map = {}
        for line in content:
            if isinstance(line, bytes):
                logger.debug("Decoding byte string...")
                line = line.decode()
            line = line.rstrip(_NEWLINE_CHARACTER)
            result = cls._process_localization_line_stat_ids(line)
            if result is not None:
                key, value = result
                lang_map[cls._LOCALIZATION_MAP[key]] = value
            result = cls._process_localization_line_unit_name(line)
            if result is not None:
                key, value = result
                unit_name_map[key] = value
        return lang_map, unit_name_map

    @classmethod
    def _read_game_data(cls) -> None:
        """Method to read game data stored on disk"""
        game_data_file_path = os.path.join(cls._DATA_PATH, cls._GAME_DATA_PATH_SUB_FOLDER)
        for game_data_file in cls._GAME_DATA_FILES:
            logger.info(f"Reading game data for {game_data_file}...")
            cls._GAME_DATA[game_data_file]: dict = _read_json_file(game_data_file_path, game_data_file)
        cls._VERSION: dict = _read_json_file(cls._DATA_PATH, cls._DATA_VERSION_FILE)

    @classmethod
    def _verify_game_data_files(cls) -> bool:
        """Validate file exists and contains data"""
        for game_data_file in cls._GAME_DATA_FILES:
            if not game_data_file.endswith('.json'):
                game_data_file = game_data_file + '.json'
            full_path = os.path.join(cls._DATA_PATH, cls._GAME_DATA_PATH_SUB_FOLDER, game_data_file)
            logger.info(f"Verifying {full_path} ...")
            if os.path.isfile(full_path):
                file_info = os.stat(full_path)
                if file_info.st_size == 0:
                    logger.warning(f"{game_data_file} exists but is empty.")
                    return False
                else:
                    logger.info(f"{game_data_file} is valid.")
            else:
                logger.error(f"{full_path} does not exist.")
                return False
        return True

    @classmethod
    def _verify_data_version_file(cls) -> bool:
        """Validate file exists and contains data"""
        if not cls._DATA_VERSION_FILE.endswith('.json'):
            data_version_file = cls._DATA_VERSION_FILE + '.json'
        else:
            data_version_file = cls._DATA_VERSION_FILE
        full_path = os.path.join(cls._DATA_PATH, data_version_file)
        if os.path.isfile(full_path):
            file_info = os.stat(full_path)
            if file_info.st_size == 0:
                logger.warning(f"{data_version_file} exists but is empty.")
                return False
            else:
                logger.info(f"{data_version_file} is valid.")
                return True
        else:
            logger.error(f"{full_path} does not exist.")
        return False

    @staticmethod
    def _write_game_data(data_path: str, file_name: str, json_data: dict) -> None:
        """Write dictionary data to file in JSON format using separate thread to prevent blocking"""
        try:
            _write_json_file(data_path, file_name, json_data)
        except IOError as io_err:
            logger.error(io_err)
        finally:
            logger.info(f"{file_name} written successfully.")

    @classmethod
    def _get_data_versions_from_file(cls) -> dict:
        if cls._verify_data_version_file():
            file_version_data = _read_json_file(cls._DATA_PATH, cls._DATA_VERSION_FILE)
            ret_dict = {"game": file_version_data['game'], "language": file_version_data['language']}
        else:
            ret_dict = {"game": None, "language": None}
        return ret_dict

    @classmethod
    def load_stats_enums_map(cls, force_reload: bool = False) -> bool:
        """Load data from statEnumMap object into statsEnum and localizationMap objects

        :param force_reload: Force reload of data from file. Defaults to False
        :type force_reload: bool
        :return: True or False depending on success or failure of data import operation
        :rtype: bool
        """

        logger.info("Loading stats_enum_map...")
        if cls._STATS_ENUM_MAP_LOADED is True and force_reload is False:
            logger.info(
                "'stats_enum_map' object is already populated. Won't load again. Use 'force_reload' to override.")
            return True
        try:
            cls._STATS_ENUM, cls._LOCALIZATION_MAP = _load_stat_enums_map_dict()
            cls.STATS_ENUMS_MAP_LOADED = True
        except DataBuilderException as e_str:
            logger.error(f"Exception caught while loading statEnumMap object: {e_str}")
            cls.STATS_ENUMS_MAP_LOADED = False
            return False
        return True

    @classmethod
    def get_attribute(cls, attribute_name: str) -> Any:
        return getattr(cls, attribute_name)

    @classmethod
    def set_attribute(cls, attr_name: str, attr_value: any) -> None:
        """Set class attribute"""
        setattr(cls, attr_name, attr_value)

    @classmethod
    def set_log_level(cls, log_level):
        """Set the logging level for message output. Default is 'INFO'"""
        log_levels = logging.getLevelNamesMapping()
        if log_level in log_levels:
            logger.setLevel(log_levels[log_level])
        else:
            raise DataBuilderException(
                f"Invalid log level {log_level}. Available options are {list(log_levels.keys())}")

    @classmethod
    def get_languages(cls) -> list:
        """Return list of current language localizations available
        :return: list of languages
        :rtype: list
        """
        return cls._VERSION['languages']

    @classmethod
    def get_unit_names_mapping(cls, language: str = "eng_us") -> dict:
        """
        Create a dictionary with unit['nameKey'] as the key and the in-game unit name as the value

        :param language: Which language to use for creating the dictionary values [Default is "eng_us"]
        :type language:str
        :return: Dictionary with unit nameKeys mapped to the in-game equivalent in the language specified
        :rtype: dict
        """
        languages_file_path = os.path.join(cls._DATA_PATH, "units")
        unit_file_name = language + "_unit_name_keys.json"
        return _read_json_file(languages_file_path, unit_file_name)

    @classmethod
    def write_data_version_file(cls) -> None:
        """Store contents of current game data version object to disk"""
        cls._write_game_data(cls._DATA_PATH, cls._DATA_VERSION_FILE, cls._VERSION)

    @staticmethod
    def _get_mastery_multiplier_name(primary_stat_id: int, tags: list) -> str:
        """Extract primary stat and non leader role and convert into string

        :param primary_stat_id: Numeric ID for primary stat to lookup
        :type primary_stat_id: int
        :param tags: List of roles assigned to a character
        :type tags: list
        :return: String created from concatenation of primary stat type and role
        :rtype:str
        """

        primary_stats = {
            2: "strength",
            3: "agility",
            4: "intelligence"
        }
        role = [x for x in tags if 'role' in x and 'leader' not in x]
        return str(primary_stats[primary_stat_id]) + '_' + role[0] + '_mastery'

    @staticmethod
    def _parse_skills(skill_list: list) -> dict:
        """Populate skill list object from data['skills']

        :param skill_list: Game data 'skills' list
        :type skill_list:
        :return: dictionary of skills
        :rtype: dict
        """

        skills = {}
        for skill in skill_list:
            s = {
                "id": skill['id'],
                "maxTier": len(skill['tier']) + 1,
                "powerOverrideTags": {},
                "isZeta": skill['isZeta'],
            }
            tier_count = 1
            for tier in skill['tier']:
                tier_count += 1
                if 'powerOverrideTag' in tier.keys():
                    s['powerOverrideTags'][str(tier_count)] = tier['powerOverrideTag']
                    tier_count = 1
            skills[skill['id']] = s
        return skills

    @staticmethod
    def _parse_xp_table_list(xp_table_list: list, data: dict) -> dict:
        for table in xp_table_list:
            tmp_table = {}
            if table['id'].startswith('crew_rating') or table['id'].startswith('galactic_power'):
                for row in table['row']:
                    idx = row['index'] + 1
                    tmp_table[str(idx)] = row['xp']
                if table['id'] == 'crew_rating_per_unit_level':
                    data['cr']['unitLevelCR'] = tmp_table
                    data['gp']['unitLevelGP'] = tmp_table
                elif table['id'] == 'crew_rating_per_ability_level':
                    data['cr']['abilityLevelCR'] = tmp_table
                    data['gp']['abilityLevelGP'] = tmp_table
                elif table['id'] == 'galactic_power_per_ship_level_table':
                    data['gp']['shipLevelGP'] = tmp_table
                elif table['id'] == 'galactic_power_per_ship_ability_level_table':
                    data['gp']['shipAbilityLevelGP'] = tmp_table
        return data

    @classmethod
    def _parse_table_list(cls, table_list: list, data: dict) -> dict:
        rarity_enum = {
            "ONE_STAR": 1,
            "TWO_STAR": 2,
            "THREE_STAR": 3,
            "FOUR_STAR": 4,
            "FIVE_STAR": 5,
            "SIX_STAR": 6,
            "SEVEN_STAR": 7
        }
        for table in table_list:
            if table['id'] == 'galactic_power_modifier_per_ship_crew_size_table':
                data['gp']['crewSizeFactor'] = {}
                for row in table['row']:
                    data['gp']['crewSizeFactor'][row['key']] = float(row['value'])
            elif table['id'] == 'crew_rating_per_unit_rarity':
                data['cr']['crewRarityCR'] = {}
                for row in table['row']:
                    data['cr']['crewRarityCR'][row['key']] = float(row['value'])
                data['gp']['unitRarityGP'] = data['cr']['crewRarityCR']
            elif table['id'] == 'crew_rating_per_gear_piece_at_tier':
                data['cr']['gearPieceCR'] = {}
                for row in table['row']:
                    data['cr']['gearPieceCR'][row['key'].replace('TIER_0', '')] = float(row['value'])
            elif table['id'] == 'galactic_power_per_complete_gear_tier_table':
                data['gp']['gearLevelGP'] = {"1": 0}
                for row in table['row']:
                    row_key = row['key'].replace('TIER_', '')
                    if row_key.startswith('0'):
                        row_key = row_key.replace('0', '')
                    data['gp']['gearLevelGP'][str(int(row_key) + 1)] = float(row['value'])
                data['cr']['gearLevelCR'] = data['gp']['gearLevelGP']
            elif table['id'] == 'galactic_power_per_tier_slot_table':
                data['gp']['gearPieceGP'] = {}
                for row in table['row']:
                    (tier, slot) = row['key'].split(':')
                    if tier not in data['gp']['gearPieceGP']:
                        data['gp']['gearPieceGP'][tier] = {}
                    slot = int(slot) - 1
                    data['gp']['gearPieceGP'][tier][slot] = float(row['value'])
            elif table['id'] == 'crew_contribution_multiplier_per_rarity':
                data['cr']['shipRarityFactor'] = {}
                for row in table['row']:
                    data['cr']['shipRarityFactor'][rarity_enum[row['key']]] = float(row['value'])
                data['gp']['shipRarityFactor'] = data['cr']['shipRarityFactor']
            elif table['id'] == 'galactic_power_per_tagged_ability_level_table':
                data['gp']['abilitySpecialGP'] = {}
                for row in table['row']:
                    data['gp']['abilitySpecialGP'][row['key']] = float(row['value'])
            elif table['id'] == 'crew_rating_per_mod_rarity_level_tier':
                data['cr']['modRarityLevelCR'] = {}
                data['gp']['modRarityLevelTierGP'] = {}
                for row in table['row']:
                    if row['key'].split(':')[-1] == "0":
                        (pips, level, tier, mod_set) = row['key'].split(':')
                        if int(tier) == 1:
                            data['cr']['modRarityLevelCR'].setdefault(pips, {})
                            data['cr']['modRarityLevelCR'][pips][level] = float(row['value'])
                        data['gp']['modRarityLevelTierGP'].setdefault(pips, {})
                        data['gp']['modRarityLevelTierGP'][pips].setdefault(level, {})
                        data['gp']['modRarityLevelTierGP'][pips][level][tier] = float(row['value'])
            elif table['id'] == 'crew_rating_modifier_per_relic_tier':
                data['cr']['relicTierLevelFactor'] = {}
                for row in table['row']:
                    data['cr']['relicTierLevelFactor'][int(row['key']) + 2] = float(row['value'])
            elif table['id'] == 'crew_rating_per_relic_tier':
                data['cr']['relicTierCR'] = {}
                for row in table['row']:
                    data['cr']['relicTierCR'][int(row['key']) + 2] = float(row['value'])
            elif table['id'] == 'galactic_power_modifier_per_relic_tier':
                data['gp']['relicTierLevelFactor'] = {}
                for row in table['row']:
                    data['gp']['relicTierLevelFactor'][int(row['key']) + 2] = float(row['value'])
            elif table['id'] == 'galactic_power_per_relic_tier':
                data['gp']['relicTierGP'] = {}
                for row in table['row']:
                    data['gp']['relicTierGP'][int(row['key']) + 2] = float(row['value'])
            elif table['id'] == 'crew_rating_modifier_per_ability_crewless_ships':
                data['cr']['crewlessAbilityFactor'] = {}
                for row in table['row']:
                    data['cr']['crewlessAbilityFactor'][row['key']] = float(row['value'])
            elif table['id'] == 'galactic_power_modifier_per_ability_crewless_ships':
                data['gp']['crewlessAbilityFactor'] = {}
                for row in table['row']:
                    data['gp']['crewlessAbilityFactor'][row['key']] = float(row['value'])
            elif table['id'].endswith('_mastery'):
                data['cr'][table['id']] = {}
                for row in table['row']:
                    data['cr'][table['id']][cls._STATS_ENUM[row['key']]] = float(row['value'])
        return data

    @staticmethod
    def _build_meta_data(meta_data):
        """Build config_map from the game meta data "config" element"""

        config_map = {}
        for cfg_item in meta_data['config']:
            config_map[cfg_item['key']] = cfg_item['value']
        return config_map

    @staticmethod
    def _build_stat_progression_list(stat_list: list) -> dict:
        stat_tables = {}
        for table in stat_list:
            if 'stattable' in table['id']:
                table_data = {}
                for stat in table['stat']['stat']:
                    table_data[stat['unitStatId']] = float(stat['unscaledDecimalValue'])
                stat_tables[table['id']] = table_data
        return stat_tables

    @staticmethod
    def _build_mod_set_data(stat_mod_set_list):
        data = {}
        for mod_set in stat_mod_set_list:
            data[mod_set['id']] = {
                'id': mod_set['completeBonus']['stat']['unitStatId'],
                'count': mod_set['setCount'],
                'value': float(mod_set['completeBonus']['stat']['unscaledDecimalValue'])
            }
        return data

    @staticmethod
    def _build_gear_data(equipment_list: list[dict]) -> dict:
        """Take equipmentList from game data and use it to populate the 'gear' element in gameData.json"""
        data = {}
        for gear in equipment_list:
            stat_list = gear['equipmentStat']['stat']
            if len(stat_list) > 0:
                data[gear['id']] = {'stats': {}}
                for stat in stat_list:
                    data[gear['id']]['stats'][stat['unitStatId']] = float(stat['unscaledDecimalValue'])
        return data

    @classmethod
    def _build_table_data(cls, table_list: list, xp_table_list: list) -> tuple[dict, dict]:
        data = {'cr': {}, 'gp': {}}
        cls._parse_table_list(table_list, data)
        cls._parse_xp_table_list(xp_table_list, data)
        return data['cr'], data['gp']

    @staticmethod
    def _build_relic_data(relic_list: list, stat_tables: dict) -> dict:
        """Extract relic details from stats table"""

        data = {}
        for relic in relic_list:
            data[relic['id']] = {"stats": {}, "gms": stat_tables[relic['relicStatTable']]}
            for stat in relic['stat']['stat']:
                data[relic['id']]['stats'][stat['unitStatId']] = float(stat['unscaledDecimalValue'])
        return data

    @staticmethod
    def _map_skills(skill_ref_list, skill_list) -> list:
        """match skill_ref_list[x]['id'] against skill_list.keys() and return the resulting list"""

        skill_ids = []
        for skill_ref in skill_ref_list:
            skill_ids.append(skill_list[skill_ref['skillId']])
        return skill_ids

    @classmethod
    def _build_unit_data(cls, units_list: list, skill_list: list, stat_tables: dict) -> dict:
        """Combine units list, skills list and stats tables into a single list of unit objects"""

        skills = DataBuilder._parse_skills(skill_list)
        base_list = []
        unit_gm_tables = {}

        for unit in units_list:
            if unit['obtainable'] is True and unit['obtainableTime'] == '0':
                unit_gm_tables[unit['baseId']] = unit_gm_tables.setdefault(unit['baseId'], {})
                unit_gm_tables[unit['baseId']][unit['rarity']] = stat_tables[unit['statProgressionId']]

                if unit['rarity'] == 1:
                    base_list.append(unit)
        data = {}
        for unit in base_list:
            if unit['combatType'] == 1:
                tier_data = {}
                relic_data = {}

                for gear_tier in unit['unitTier']:
                    tier_data[gear_tier['tier']] = {'gear': gear_tier['equipmentSet'], 'stats': {}}
                    for stat in gear_tier['baseStat']['stat']:
                        tier_data[gear_tier['tier']]['stats'][stat['unitStatId']] = float(stat['unscaledDecimalValue'])
                for tier in unit['relicDefinition']['relicTierDefinitionId']:
                    # Example tier string 'TAC_SUP_RELIC_TIER_08', strip the last two digits, convert to number and
                    # add 2 for offset from relic unlock state in game
                    relic_data[int(tier[-2:]) + 2] = tier
                data[unit['baseId']] = {
                    'combatType': 1,
                    'primaryStat': unit['primaryUnitStat'],
                    'gearLvl': tier_data,
                    'growthModifiers': unit_gm_tables[unit['baseId']],
                    'skills': cls._map_skills(unit['skillReference'], skills),
                    'relic': relic_data,
                    'masteryModifierID': cls._get_mastery_multiplier_name(unit['primaryUnitStat'], unit['categoryId'])
                }
            else:
                stats = {}
                for stat in unit['baseStat']['stat']:
                    stats[stat['unitStatId']] = float(stat['unscaledDecimalValue'])
                ship = {
                    'combatType': 2,
                    'primaryStat': unit['primaryUnitStat'],
                    'stats': stats,
                    'growthModifiers': unit_gm_tables[unit['baseId']],
                    'skills': cls._map_skills(unit['skillReference'], skills),
                    'crewStats': stat_tables[unit['crewContributionTableId']],
                    'crew': []
                }
                for crew in unit['crew']:
                    ship['crew'].append(crew['unitId'])
                    for s in crew['skillReference']:
                        ship['skills'].append(skills[s['skillId']])
                data[unit['baseId']] = ship
        return data

    @classmethod
    def _build_data(cls, data):
        """Take game data dictionary and parse into just the needed tables"""

        game_data = {}
        logger.info("Building stat_tables from statProgression")
        stat_tables = cls._build_stat_progression_list(data['statProgression'])

        logger.info("Building modSetData from equipment list")
        game_data['modSetData'] = cls._build_mod_set_data(data['statModSet'])
        logger.info("Building crTables and gpTables")
        (game_data['crTables'], game_data['gpTables']) = cls._build_table_data(data['table'], data['xpTable'])

        logger.info("Building gearData from equipment list")
        game_data['gearData'] = cls._build_gear_data(data['equipment'])
        logger.info("Building relicData from relicTierDefinition list")
        game_data['relicData'] = cls._build_relic_data(data['relicTierDefinition'], stat_tables)
        logger.info("Building unitData from units and skill lists")
        game_data['unitData'] = cls._build_unit_data(data['units'], data['skill'], stat_tables)
        return game_data

    @classmethod
    def get_game_data(cls) -> dict or None:
        """Load game data objects from JSON file or build from game servers. Return a collection of dictionaries
        representing the unitData, gearData, modSetData, crTables, gpTables and relicData. Primary intended use
        is by the StatCalc library for initializing internal data structures for roster calculations.

        """
        if cls._INITIALIZED is False:
            raise DataBuilderException(f"DataBuilder has not yet been initialized. Please perform that action first.")
        if cls._verify_game_data_files() is False:
            cls.update_game_data()
        else:
            cls._read_game_data()
        return cls._GAME_DATA

    @classmethod
    def update_game_data(cls):
        """Get the latest game data from servers"""

        logger.info("Getting game data from comlink instance")
        start_time = time.perf_counter()
        game_data = cls._COMLINK.get_game_data(include_pve_units=False)
        end_time = time.perf_counter()
        logger.debug(f"Game data retrieval completed in {end_time - start_time:.2f} seconds.")

        logger.info("Building data constructs from game data...")
        cls._GAME_DATA = cls._build_data(game_data)

        logger.info(f"Validating that required data file paths exist.")
        cls._validate_data_file_paths()

        logger.info("*** Writing game data files to disk... ***")
        for game_data_file in cls._GAME_DATA_FILES:
            logger.info(f"... Writing game data file: {game_data_file} ...")
            target_directory = os.path.join(cls._DATA_PATH, cls._GAME_DATA_PATH_SUB_FOLDER)
            cls._write_game_data(target_directory, game_data_file, cls._GAME_DATA.get(game_data_file, {}))

        logger.info("*** Writing game version information to disk... ***")
        _write_json_file(cls._DATA_PATH, cls._DATA_VERSION_FILE, cls._VERSION)

    @classmethod
    def update_localization_bundle(cls, force_update: bool = False):
        """Collect localization bundle from game servers.

        :param force_update: Flag to indicate whether existing files should be overwritten. Defaults to False
        :type force_update: bool
        """
        logger.info("Updating localization bundle...")
        server_versions = cls._COMLINK.get_latest_game_data_version()

        current_versions = cls._get_data_versions_from_file()
        if current_versions == server_versions:
            logger.warning(f"The current server game versions are the same as those in {cls._DATA_VERSION_FILE}")
            if force_update is False:
                logger.warning(f"The 'force_update' flag is set to '{force_update}'. Data files contain most" +
                               " current data.")
                return

        cls._VERSION['game'] = server_versions['game']
        cls._VERSION['language'] = server_versions['language']

        cls._VERSION['languages'] = []

        logger.info(f"Validating that required data file paths exist.")
        cls._validate_data_file_paths()

        logger.info(f"Collecting bundle from game servers. " +
                    f"Language version: '{server_versions['language']}', USE_UNZIP = '{cls._USE_UNZIP}'")
        loc_bundle = cls._COMLINK.get_localization_bundle(id=server_versions['language'], unzip=cls._USE_UNZIP)

        zip_obj = None
        if cls._USE_UNZIP is False:
            logger.info("Decoding Base64 data...")
            loc_bundle_decoded = base64.b64decode(loc_bundle['localizationBundle'])
            logger.info("Decompressing data stream...")
            zip_obj = zipfile.ZipFile(io.BytesIO(loc_bundle_decoded))
            language_files = zip_obj.namelist()
        else:
            language_files = list(loc_bundle.keys())

        for language in language_files:
            if cls._USE_UNZIP is True:
                contents = loc_bundle[language]
            else:
                with zip_obj.open(language) as lang_file:
                    contents = lang_file.readlines()
            lang_name = language.replace('Loc_', '').replace('.txt', '').lower()
            name_key_file = f"{lang_name}_unit_name_keys"
            lang_map, name_key_map = cls._process_file_contents_by_line(contents)

            for (file_name, data_map, path) in [(lang_name, lang_map, '/languages'),
                                                (name_key_file, name_key_map, '/units')]:
                logger.info(f"Writing {file_name} data to disk.")
                _write_json_file(f"{cls._DATA_PATH + path}", file_name, data_map)
            if lang_name not in cls._LANGUAGE_FILE_SKIP_LIST:
                cls._VERSION['languages'].append(lang_name)

        if cls._STATS_ENUM_MAP_LOADED is False:
            logger.info(f"stats_enum_map not loaded. Loading now...")
            cls.load_stats_enums_map()

        stat_enums = {}
        logger.debug(f"{cls._LOCALIZATION_MAP=}")
        for key, value in cls._LOCALIZATION_MAP.items():
            stat_enums[value] = key

        logger.info("Writing game version information to disk...")
        _write_json_file(cls._DATA_PATH, cls._DATA_VERSION_FILE, cls._VERSION)

    @classmethod
    def enable_auto_game_data_update(cls, interval: int = None) -> bool:
        """Turn the automatic data file update thread on

        :param interval: Time in minutes to wait between polling cycles for new data
        :type interval: int
        :return: True if successful, False otherwise
        :rtype: bool
        """
        if cls._AUTO_UPDATE_GAME_DATA is True:
            logger.info(f"Auto update is already enabled")
            return True
        cls._AUTO_UPDATE_GAME_DATA = True

        if interval is not None:
            cls._AUTO_UPDATE_GAME_DATA_INTERVAL = interval

        logger.info(f"Enabling automatic data updates at {cls._AUTO_UPDATE_GAME_DATA_INTERVAL} minute interval.")
        if cls._AUTO_UPDATE_GAME_DATA_THREAD_NAME is None:
            logger.info("No existing auto update thread found. Creating a new one.")
            result = cls._start_auto_update_thread()
            if result is True:
                logger.info(f"Auto data update thread [{cls._AUTO_UPDATE_GAME_DATA_THREAD_NAME}] created successfully.")
                return True
            else:
                logger.error(f"Auto data update thread [{cls._AUTO_UPDATE_GAME_DATA_THREAD_NAME}] failed to start.")
                return False
        else:
            logger.info(f"Auto data update thread [{cls._AUTO_UPDATE_GAME_DATA_THREAD_NAME}] is already running.")
            return True

    @classmethod
    def disable_auto_game_data_update_thread(cls) -> bool:
        """Turn the automatic game data file update thread off"""
        if cls._AUTO_UPDATE_GAME_DATA is False:
            logger.info("Automatic game data updates are currently disabled.")
            return True
        logger.info("Disabling automatic game data updates...")
        cls._AUTO_UPDATE_GAME_DATA = False

    @classmethod
    def set_auto_game_data_update_interval(cls, minutes: int = None) -> None:
        """Set the automatic game data update interval in minutes. Default is 60 minutes."""
        if not isinstance(minutes, int):
            logger.error(f"Value for the minutes argument should be 'int', not {type(minutes)}")
            raise DataBuilderRuntimeError(f"Value for the minutes argument should be 'int', not {type(minutes)}")
        logger.info(f"Updating automatic game data update interval to {str(minutes)} minutes.")
        current_interval = str(cls._AUTO_UPDATE_GAME_DATA_INTERVAL)
        cls._AUTO_UPDATE_GAME_DATA_INTERVAL = minutes
        new_interval = str(cls._AUTO_UPDATE_GAME_DATA_INTERVAL)
        logger.info(f"Automatic game data update interval changed from {current_interval} to {new_interval}.")

    @classmethod
    def _validate_data_file_paths(cls) -> None:
        for path in cls._DATA_FILE_PATHS:
            logger.info(f"Verifying that {path} exists...")
            _verify_data_path(path)
            logger.info(f"Path validation for {path} complete.")

    @classmethod
    def is_initialized(cls) -> bool:
        return cls._INITIALIZED

    @classmethod
    def initialize(cls, **kwargs) -> bool:
        """Prepare DataBuilder environment for first use. Providing keyword arguments can override default settings.

        data_path: str Defaults to './data'
        data_version_file: str Defaults to 'dataVersion.json',
        game_data_path_sub_folder: str Defaults to 'game',
        zip_game_data: bool Defaults to False,
        use_segments: bool Defaults to False,
        use_unzip: bool Defaults to False,

        """
        allowed_parameters = [
            'comlink_url',
            'comlink_stats_url,'
            'data_path',
            'data_version_file',
            'game_data_path_sub_folder',
            'zip_game_data',
            'use_segments',
            'use_unzip',
        ]
        logger.info("Initializing DataBuilder for first time use.")
        class_vars = vars(cls)
        logger.debug(f"Class vars: {class_vars.keys()}")
        for param, value in kwargs.items():
            if param in allowed_parameters:
                class_var = '_' + param.upper()
                logger.debug(f"Setting class variable {class_var} to {value}")
                # Remove .json file extension from file name arguments since it is added by the read/write methods
                if value.endswith('.json'):
                    value = value.replace('.json', '')
                logger.debug(f"Before: {class_var} = {class_vars[class_var]}")
                setattr(cls, class_var, value)
                new_vars = vars(cls)
                logger.debug(f"After: {class_var} = {new_vars[class_var]}")

        # Ensure that required data file paths exist on the filesystem
        cls._validate_data_file_paths()

        logger.info("Loading stat_enums_map.")
        if cls.load_stats_enums_map():
            logger.info("stat_enums_map loaded successfully.")
        else:
            logger.error("stat_enums_map failed to load. Exiting.")
            raise DataBuilderRuntimeError("'stat_enums_map' failed to load.")

        logger.info("Checking for game data files")
        data_files_exist = cls._verify_game_data_files()
        if data_files_exist is True:
            logger.info("Reading game data from files")
            cls._read_game_data()
        else:
            logger.info("Updating game data from servers.")
            cls.update_game_data()
            logger.info("Updating localization data from servers.")
            cls.update_localization_bundle()
            logger.info("Writing game version information to disk...")
            _write_json_file(cls._DATA_PATH, cls._DATA_VERSION_FILE, cls._VERSION)
        cls._INITIALIZED = True
        return True
