# coding=utf-8
"""
Helper objects and functions for swgoh_comlink
"""
from enum import IntFlag, auto


class DataItems(IntFlag):
    """
    Integer flag enum class mapping game data collection names to the integer values of their bit positions for use
    in the `items` parameter of the `get_game_data()` method.

    Since the member values are integers, they can be combined using normal integer arithmetic operations to specify
    more than one collection in a single call.

    Examples:
        effect = comlink.get_game_data(items=DataItems.EFFECT)
        skill_equipment = comlink.get_game_data(items=(DataItems.SKILL + DataItems.EQUIPMENT))
        units_no_pve = comlink.get_game_data(items=DataItems.UNITS, include_pve_units=False)

    Some of the DataItems members are actually aliases for other members. For example, the `TABLE` member is an
    alias for the `XP_TABLE` member. This is done because both members represent the same collection in the game data.

    Other members are provided as a convenience. For example, the `SEGMENT1` member is assigned the integer value of
    all the collections that are included when using the original (request_segment=) style of calling the
    `get_game_data()` method.

    To retrieve all of the available game data, use the `DataItems.ALL` member.

    A list of the member names of the DataItems class can be retrieved using the `DataItems.members()` class method.
    """

    ALL = -1
    CATEGORY = 1
    UNLOCK_ANNOUNCEMENT_DEFINITION = auto()
    SKILL = auto()
    EQUIPMENT = auto()
    EFFECT = auto()
    XP_TABLE = auto()
    TABLE = XP_TABLE
    BATTLE_ENVIRONMENTS = auto()
    EVENT_SAMPLING = auto()
    TARGETING_SET = auto()
    REQUIREMENT = auto()
    POWER_UP_BUNDLE = auto()
    GUILD_BANNER = auto()
    BATTLE_TARGETING_RULE = auto()
    PERSISTENT_VFX = auto()
    MATERIAL = auto()
    PLAYER_TITLE = auto()
    PLAYER_PORTRAIT = auto()
    TIME_ZONE_CHANGE_CONFIG = auto()
    ENVIRONMENT_COLLECTION = auto()
    EFFECT_ICON_PRIORITY = auto()
    SOCIAL_STATUS = auto()
    ABILITY = auto()
    STAT_PROGRESSION = auto()
    CHALLENGE = auto()
    CHALLENGE_STYLE = CHALLENGE
    WAR_DEFINITION = auto()
    STAT_MOD_SET = auto()
    STAT_MOD = STAT_MOD_SET
    RECIPE = auto()
    MOD_RECOMMENDATION = auto()
    SCAVENGER_CONVERSION_SET = auto()
    GUILD = auto()
    RAID_CONFIG = GUILD
    GUILD_RAID = GUILD
    GUILD_EXCHANGE_ITEM = GUILD
    TERRITORY_BATTLE_DEFINITION = GUILD
    TERRITORY_WAR_DEFINITION = GUILD
    STARTER_GUILD = GUILD
    TERRITORY_TOURNAMENT_DEFINITION = GUILD
    SEASON_DEFINITION = GUILD
    SEASON_LEAGUE_DEFINITION = GUILD
    SEASON_DIVISION_DEFINITION = GUILD
    SEASON_REWARD_TABLE = GUILD
    TERRITORY_TOURNAMENT_LEAGUE_DEFINITION = GUILD
    TERRITORY_TOURNAMENT_DIVISION_DEFINITION = GUILD
    SAVED_SQUAD_CONFIG = GUILD
    GUILD_RAID_GLOBAL_CONFIG = GUILD
    MYSTERY_BOX = auto()
    MYSTERY_STAT_MOD = MYSTERY_BOX
    COOLDOWN = auto()
    DAILY_ACTION_CAP = auto()
    ENERGY_REWARD = auto()
    UNIT_GUIDE_DEFINITION = auto()
    GALACTIC_BUNDLE = auto()
    LINKED_STORE_ITEM = GALACTIC_BUNDLE
    RELIC_TIER_DEFINITION = auto()
    UNITS = auto()
    CAMPAIGN = auto()
    CONQUEST = auto()
    CONQUEST_DEFINITION = CONQUEST
    CONQUEST_MISSION = CONQUEST
    ARTIFACT_DEFINITION = CONQUEST
    CONSUMABLE_DEFINITION = CONQUEST
    CONSUMABLE_TYPE = CONQUEST
    ARTIFACT_TIER_DEFINITION = CONQUEST
    CONSUMABLE_TIER_DEFINITION = CONQUEST
    RECOMMENDED_SQUAD = auto()
    UNIT_GUIDE_LAYOUT = auto()
    DAILY_LOGIN_REWARD_DEFINITION = auto()
    CALENDAR_CATEGORY_DEFINITION = auto()
    TERRITORY_TOURNAMENT_DAILY_REWARD_TABLE = auto()
    DATACRON = auto()
    DATACRON_SET = DATACRON
    DATACRON_TEMPLATE = DATACRON
    DATACRON_AFFIX_TEMPLATE_SET = DATACRON
    DATACRON_HELP_ENTRY = DATACRON
    DISPLAYABLE_ENEMY = auto()
    EPISODE_DEFINITION = auto()
    LINKING_REWARD = auto()

    SEGMENT1 = 2097151
    SEGMENT2 = 68717379584
    SEGMENT3 = 206158430208
    SEGMENT4 = 281200098803712

    @classmethod
    def members(cls):
        """Return a list of the member names of the DataItems class."""
        return cls.__members__.keys()


class Constants:
    ALL = -1
    CategoryDefinitions = 1
    UnlockAnnouncements = 2
    SkillDefinitions = 4
    EquipmentDefinitions = 8
    BattleEffectDefinitions = 16
    AllTables = 32
    EnvironmentDefinitions = 64
    EventSampling = 128
    BattleTargetingSets = 256
    Requirements = 512
    PowerUpBundles = 1024
    GuildBannerDefinition = 2048
    BattleTargetingRules = 4096
    PersistentVFX = 8192
    CraftingMaterialDefinitions = 16384
    PlayerTitleDefinitions = 32768
    PlayerPortraitDefinitions = 65536
    TimeZoneChangeConfig = 131072
    EnvironmentCollections = 262144
    PersistentEffectPriorities = 524288
    SocialStatus = 1048576

    AbilityDefinitions = 2097152
    StatProgression = 4194304
    Challenge = 8388608
    WarDefinitions = 16777216
    StatMod = 33554432
    RecipeDefinitions = 67108864
    ModRecommendations = 134217728
    ScavengerConversionSets = 268435456
    Guild = 536870912
    Mystery = 1073741824
    CooldownDefinitions = 2147483648
    DailyActionCapDefinitions = 4294967296
    EnergyRewards = 8589934592
    UnitGuideDefinitions = 17179869184
    GalacticBundleDefinitions = 34359738368

    RelicTierDefinitions = 68719476736
    UnitDefinitions = 137438953472

    CampaignDefinitions = 274877906944
    Conquest = 549755813888
    AbilityDecisionTrees = 1099511627776
    RecommendedSquads = 2199023255552
    UnitGuideLayouts = 4398046511104
    DailyLoginRewardDefinitions = 8796093022208
    CalendarCategories = 17592186044416
    TerritoryTournamentDailyRewards = 35184372088832
    DatacronDefinitions = 70368744177664
    DisplayableEnemyDefinitions = 140737488355328

    Help = -9223372036854775808
    Segment1 = 2097151
    Segment2 = 68717379584
    Segment3 = 206158430208
    Segment4 = 281200098803712
    UBSUpdate = 2150109456

    @classmethod
    def get(cls, item):
        return str(getattr(cls, item)) if getattr(cls, item, None) else None

    @classmethod
    def get_names(cls):
        return [x for x in list(cls.__dict__.keys()) if not x.startswith('_') and
                not isinstance(cls.__dict__[x], classmethod)]


def get_raid_leaderboard_ids(campaign_data: list) -> list[str]:
    """
    Extracts and returns the raid leaderboard IDs from the provided campaign data.

    This function processes the `campaign_data` to find and extract the IDs of
    raids associated with the guild campaigns. The IDs are formatted as a string
    specifying the type and structure of the raid. The function specifically works
    with the "GUILD" campaign type and retrieves IDs from the "NORMAL_DIFF"
    difficulty group.

    Args:
        campaign_data (list): A list of campaign data structures, where each
            structure represents campaign information. The input data is
            expected to have nested dictionaries and lists with specific keys
            such as 'id', 'campaignMap', 'campaignNodeDifficultyGroup', and
            'campaignNode'.

    Returns:
        list: A list containing formatted raid leaderboard IDs extracted from the
        guild campaign data. Each ID is constructed as a string containing the
        relevant identifiers for the campaign and its raids.

    Raises:
        KeyError: If any of the required keys (e.g., 'id', 'campaignMap',
            etc.) are missing in the input data.
        TypeError: If `campaign_data` is not structured as expected, such as if
            it is not a list or contains improperly formatted elements.
    """
    raid_ids = []
    guild_campaigns = next((item for item in campaign_data if item.get('id') == 'GUILD'), None)
    for raid in guild_campaigns['campaignMap'][0]['campaignNodeDifficultyGroup'][0]['campaignNode']:
        for mission in raid['campaignNodeMission']:
            elements = [
                    guild_campaigns['id'],
                    guild_campaigns['campaignMap'][0]['id'],
                    "NORMAL_DIFF",
                    raid['id'],
                    mission['id']
            ]
            raid_ids.append(":".join(elements))
    return raid_ids
