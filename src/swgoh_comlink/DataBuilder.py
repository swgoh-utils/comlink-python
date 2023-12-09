"""
Python library module for building data files that can be used by the StatCalc module in the swgoh_comlink package.
"""

import base64
import io
import json
import logging
import os
import re
import time
import zipfile

from swgoh_comlink import SwgohComlink, Utils

logger = Utils.get_logger()

_COMMENT_START = '#'
_FIELD_SEPARATOR = '|'
_NEWLINE_CHARACTER = '\n'
_PRE_PATTERN = re.compile(r'^\[[0-9A-F]*?]')
_POST_PATTERN = re.compile(r'\s+\(([A-Z]+)\)\[-]$')


def _verify_data_path(data_path: str) -> bool:
    """Validate data path and create if not found"""

    try:
        os.mkdir(data_path)
    except FileExistsError:
        logger.info(f"{data_path} exists.")
        return True
    except FileNotFoundError as path_err_str:
        logger.error(f"A parent folder in {data_path} does not exist. Please verify the path. [{path_err_str}]")
        return False


def _verify_game_data_file(data_path: str, file_name: str) -> bool:
    """Validate file exists and contains data"""

    file_name = file_name + '.json'
    full_path = os.path.join(data_path, file_name)
    if os.path.isfile(full_path):
        file_info = os.stat(full_path)
        if file_info.st_size == 0:
            logger.warning(f"{file_name} exists but is empty.")
            return False
        else:
            logger.info(f"{file_name} is valid.")
            return True
    else:
        logger.error(f"{file_name} does not exist in {data_path}.")
        return False


def _write_json_file(data_path: str, file_name: str, json_data: dict) -> None:
    """Method to write file contents to disk"""

    logger.info(f"File write args received: {data_path=}, {file_name=}")
    if not file_name.endswith('.json'):
        file_name = file_name + '.json'
    full_path = os.path.join(data_path, file_name)
    if os.path.isfile(full_path):
        file_name_bak = file_name + '-' + time.strftime("%Y%m%d_%H%M%S", time.localtime()) + '.bak'
        logger.info(f"{file_name} already exists. Renaming to {file_name_bak} before saving.")
        full_name_bak = os.path.join(data_path, file_name_bak)
        os.rename(full_path, full_name_bak)
    try:
        logger.info(f"Opening {full_path}...")
        with open(full_path, 'w') as fn:
            json.dump(json_data, fn, indent=2)
    except Exception as e_str:
        logger.error(f"Exception caught: {e_str}")
        raise e_str
    logger.info(f"{file_name} written successfully.")
    return


def _read_json_file(data_path: str, file_name: str) -> dict:
    """Retrieve JSON data from file and return dictionary"""

    if not file_name.endswith('.json'):
        file_name = file_name + '.json'
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


class DataBuilderException(Exception):
    pass


class DataBuilderRuntimeError(RuntimeError):
    pass


class DataBuilder:
    """Base container class representing a collection of methods for managing game data files populated with information
    retrieved from the game servers directly. This class is not intended to be instantiated.

    """

    _VERSION = {}
    _STATS_ENUM = {}
    _DATA_PATH = os.path.join(os.getcwd(), 'data')
    _GAME_DATA = {}
    _ZIP_GAME_DATA = False
    _USE_SEGMENTS = False
    _USE_UNZIP = False
    _LOCALIZATION_MAP = {}
    _DATA_VERSION_FILE = 'dataVersion'
    _GAME_DATA_FILE = 'gameData'
    _STATS_ENUM_MAP_LOADED = False
    _LOG_LEVEL = 'INFO'
    _COMLINK = SwgohComlink()

    @classmethod
    def _process_localization_line(cls, loc_line: str):
        if cls._is_comment_or_invalid(loc_line):
            return

        loc_line = loc_line.rstrip(_NEWLINE_CHARACTER)
        logger.debug(f"Location line to be split {loc_line=}")
        key, value = loc_line.split(_FIELD_SEPARATOR)
        logger.debug(f"{key=} {value=}")

        if not key or not value:
            return

        if key not in cls._LOCALIZATION_MAP.keys():
            return

        value = cls._apply_value_patterns(value)

        logger.debug(f"Returning {key=} {value=}")
        return key, value

    @classmethod
    def _is_comment_or_invalid(cls, loc_line: str) -> bool:
        return loc_line.startswith(_COMMENT_START) or _FIELD_SEPARATOR not in loc_line

    @classmethod
    def _apply_value_patterns(cls, value: str) -> str:
        value = _PRE_PATTERN.sub('', value)
        value = _POST_PATTERN.sub('', value)
        return '' if value is None else value

    @classmethod
    def _process_file_contents_by_line(cls, content: list) -> dict:
        """Iterate through file contents list and create language map from information contained within"""
        logger.info("Processing language content...")
        lang_map = {}
        for line in content:
            if isinstance(line, bytes):
                logger.debug("Decoding byte string...")
                line = line.decode()
            line = line.rstrip(_NEWLINE_CHARACTER)
            result = cls._process_localization_line(line)
            if result is not None:
                key, value = result
                lang_map[cls._LOCALIZATION_MAP[key]] = value
        return lang_map

    @staticmethod
    def _read_game_data(data_path: str, game_data_file: str, data_version_file: str,
                        stat_enum_file: str) -> tuple:
        """Method to read game data stored on disk"""
        game_data = _read_json_file(data_path, game_data_file)
        _version = _read_json_file(data_path, data_version_file)
        stat_enum = _read_json_file(data_path, stat_enum_file)

        return game_data, _version, stat_enum

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
    def set_attribute(cls, attr_name: str, attr_value: any):
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
        return str(primary_stats[primary_stat_id]) + '_' + role[0]

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
            tnp_table = {}
            if 'crew_rating' in table['id'] or 'galactic_power' in table['id']:
                for row in table['row']:
                    tnp_table[row['index']] = row['xp']
                if table['id'] == 'crew_rating_per_unit_level':
                    data['cr']['unitLevelCR'] = tnp_table
                    data['gp']['unitLevelGP'] = tnp_table
                elif table['id'] == 'crew_rating_per_ability_level':
                    data['cr']['abilityLevelCR'] = tnp_table
                    data['gp']['abilityLevelGP'] = tnp_table
                elif table['id'] == 'galactic_power_per_ship_level_table':
                    data['gp']['shipLevelGP'] = tnp_table
                elif table['id'] == 'galactic_power_per_ship_ability_level_table':
                    data['gp']['shipAbilityLevelGP'] = tnp_table
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
                data['gp']['gearLevelGP'] = {1: 0}
                for row in table['row']:
                    data['gp']['gearLevelGP'][row['key'].replace('TIER_0', '')] = float(row['value'])
                data['cr']['gearLevelCR'] = data['gp']['gearLevelGP']
            elif table['id'] == 'galactic_power_per_tier_slot_table':
                data['gp']['gearPieceGP'] = {}
                g = {}
                for row in table['row']:
                    (tier, slot) = row['key'].split(':')
                    if tier not in g.keys():
                        g[tier] = {}
                    slot = int(slot) - 1
                    g[tier][slot] = int(row['value'])
            elif table['id'] == 'crew_contribution_multiplier_per_rarity':
                data['cr']['shipRarityFactor'] = {}
                for row in table['row']:
                    data['cr']['shipRarityFactor'][rarity_enum[row['key']]] = float(row['value'])
                data['gp']['shipRarityFactor'] = data['cr']['shipRarityFactor']
            elif table['id'] == 'galactic_power_per_tagged_ability_level_table':
                data['gp']['abilitySpecialGP'] = {}
                g = {}
                for row in table['row']:
                    g[row['key']] = float(row['value'])
            elif table['id'] == 'crew_rating_per_mod_rarity_level_tier':
                data['cr']['modRarityLevelCR'] = {}
                c = {}
                data['gp']['modRarityLevelTierGP'] = {}
                g = {}
                for row in table['row']:
                    if row['key'].split(':')[-1] == "0":
                        (pips, level, tier, mod_set) = row['key'].split(':')
                        if int(tier) == 1:
                            c.setdefault(pips, {})
                            c[pips][level] = float(row['value'])
                        g.setdefault(pips, {})
                        g[pips].setdefault(level, {})
                        g[pips][level][tier] = float(row['value'])
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
                    table_data[stat['unitStatId']] = int(stat['unscaledDecimalValue'])
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
    def _build_gear_data(equipment_list):
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
    def _build_table_data(cls, table_list, xp_table_list):
        data = {'cr': {}, 'gp': {}}
        return cls._parse_table_list(table_list, data), cls._parse_xp_table_list(xp_table_list, data)

    @staticmethod
    def _build_relic_data(relic_list: list, stat_tables: dict) -> dict:
        """Extract relic details from stats table"""

        data = {}
        for relic in relic_list:
            data[relic['id']] = {"stats": {}, "gms": stat_tables[relic['relicStatTable']]}
            for stat in relic['stat']['stat']:
                data[relic['id']]['stats']['unitStatId'] = float(stat['unscaledDecimalValue'])
        return data

    @staticmethod
    def _map_skills(skill_ref_list, skill_list):
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
            if unit['obtainable'] == 'True' and unit['obtainableTime'] == '0':
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
    def set_game_data(cls) -> dict:
        """Load game data objects from JSON file or build from game servers. Return a collection of dictionaries
        representing the unitData, gearData, modSetData, crTables, gpTables and relicData. Primary intended use
        is by the StatCalc library for initializing internal data structures for roster calculations.

        """
        if not os.path.isfile(os.path.join(cls._DATA_PATH, 'gameData.json')):
            logger.info(f"gameData.json file not found. Collecting data from game servers.")
            cls.update_game_data()
        return _read_json_file(cls._DATA_PATH, 'gameData.json')

    @classmethod
    def update_game_data(cls):
        """Get the latest game data from servers"""

        logger.info("Getting game data from comlink instance")
        start_time = time.perf_counter()
        game_data = cls._COMLINK.get_game_data()
        end_time = time.perf_counter()
        logger.debug(f"Game data retrieval completed in {end_time - start_time:.2} seconds.")

        logger.info("Building data constructions from game data...")
        cls._GAME_DATA = cls._build_data(game_data)
        logger.info("Writing game data to disk...")
        _write_json_file(cls._DATA_PATH, 'gameData.json', cls._GAME_DATA)

    @classmethod
    def update_localization_bundle(cls, version_string: str = None):
        """Collect localization bundle from game servers.

        :param version_string: The localization bundle version to collect. Defaults to latest version.
        :type version_string: str
        """
        logger.info("Updating localization bundle...")
        if version_string is None:
            latest_version = cls._COMLINK.get_latest_game_data_version()
            version_string = latest_version['language']

        logger.info(f"Collecting bundle from game servers. {version_string=}, USE_UNZIP={cls._USE_UNZIP}")
        loc_bundle = cls._COMLINK.get_localization_bundle(id=version_string, unzip=cls._USE_UNZIP)
        cls._VERSION['language'] = version_string
        cls._VERSION['languages'] = []

        if cls._STATS_ENUM_MAP_LOADED is False:
            logger.info(f"stats_enum_map not loaded. Loading now...")
            cls.load_stats_enums_map()

        stat_enums = {}
        logger.debug(f"{cls._LOCALIZATION_MAP=}")
        for key, value in cls._LOCALIZATION_MAP.items():
            stat_enums[value] = key
        logger.info("Writing statEnum.json file to disk.")
        logger.debug(f"{stat_enums=}")
        _write_json_file(cls._DATA_PATH, 'statEnum.json', stat_enums)

        if cls._USE_UNZIP is True:
            for lang, contents in loc_bundle.items():
                lang = lang.replace('Loc_', '')
                lang = lang.replace('.txt', '').lower()
                lang_map = cls._process_file_contents_by_line(contents)
                logger.info(f"Writing {lang} data to disk.")
                _write_json_file(cls._DATA_PATH, lang, lang_map)
                cls._VERSION['languages'].append(lang)
        else:
            logger.info("Decoding Base64 data...")
            loc_bundle_decoded = base64.b64decode(loc_bundle['localizationBundle'])
            logger.info("Decompressing data stream...")
            zip_obj = zipfile.ZipFile(io.BytesIO(loc_bundle_decoded))
            lang_list = zip_obj.namelist()
            for lang in lang_list:
                if 'Key_Mapping' in lang:
                    continue
                lang_name = lang.replace('Loc_', '')
                lang_name = lang_name.replace('.txt', '').lower()
                logger.info(f"Processing {lang_name} data...")
                with zip_obj.open(lang) as lang_file:
                    contents = lang_file.readlines()
                lang_map = cls._process_file_contents_by_line(contents)
                logger.info(f"Writing {lang_name} data to disk.")
                _write_json_file(cls._DATA_PATH, lang_name, lang_map)
                cls._VERSION['languages'].append(lang)

    @classmethod
    def initialize(cls, **kwargs) -> bool:
        """Prepare DataBuilder environment for first use. Providing keyword arguments can override default settings.

        data_path: str Defaults to './data'
        stat_enums_map_file: str Defaults to 'statEnumsMap.json',
        stat_enum_file: str Defaults to 'statEnum.json',
        data_version_file: str Defaults to 'dataVersion.json',
        game_data_file: str Defaults to 'gameData.json',
        zip_game_data: bool Defaults to False,
        use_segments: bool Defaults to False,
        use_unzip: bool Defaults to False,

        """
        allowed_parameters = [
            'data_path',
            'stat_enums_map_file',
            'stat_enum_file',
            'data_version_file',
            'game_data_file',
            'zip_game_data',
            'use_segments',
            'use_unzip',
        ]
        GAME_DATA_FILES = [cls._GAME_DATA_FILE, cls._DATA_VERSION_FILE]
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
        logger.info("Verifying 'data_path'")
        if _verify_data_path(cls._DATA_PATH):
            logger.info(f"Data path {cls._DATA_PATH} exists.")
        else:
            logger.info(f"Data path {cls._DATA_PATH} does not exist. Please verify the value provided.")
            raise DataBuilderRuntimeError(
                f"Data path {cls._DATA_PATH} does not exist. Please verify the value provided.")
        logger.info("Loading stat_enums_map.")
        if cls.load_stats_enums_map():
            logger.info("stat_enums_map loaded successfully.")
        else:
            logger.error("stat_enums_map failed to load. Exiting.")
            raise DataBuilderRuntimeError("'stat_enums_map' failed to load.")
        logger.info("Checking for game data files")
        DATA_FILES_EXIST = False
        for file in GAME_DATA_FILES:
            if _verify_game_data_file(cls._DATA_PATH, file):
                logger.info(f"{file} verified")
                DATA_FILES_EXIST = True
            else:
                logger.error(f"Unable to verify {file}. Game data must be collected from game servers.")
                DATA_FILES_EXIST = False
        if DATA_FILES_EXIST is True:
            logger.info("Reading game data from files")
            cls._GAME_DATA, cls._VERSION = cls._read_game_data(cls._DATA_PATH, *GAME_DATA_FILES)
        else:
            logger.info("Updating game data from servers.")
            cls.update_game_data()
        return True
