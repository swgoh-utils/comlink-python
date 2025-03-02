# coding=utf-8
"""
Helper objects and functions for swgoh_comlink
"""


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
    PlayerPortaitDefinitions = 65536
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
