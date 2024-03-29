"""
get_player.py
Script to illustrate the basic usage of the swgoh_comlink wrapper library
"""
# import the SwgohComlink class from the swgoh_comlink module
from swgoh_comlink import SwgohComlink

# create an instance of a SwgohComlink object
comlink = SwgohComlink()

"""
# Call the get_player() method of the SwgohComlink instance for a specific player ID or allyCode.
# We use allyCode in this example.

The result is a dictionary with the following top level keys:

    {
        'allyCode': '314927874',
        'datacron': [...],
        'guildBannerColor': 'bright_blue_dark_blue',
        'guildBannerLogo': 'guild_icon_flame',
        'guildId': '8RhppbbqR_ShmjY5S6ZtQg',
        'guildLogoBackground': '',
        'guildName': 'sL Dead Forest Guards',
        'guildTypeId': 'NORMAL',
        'lastActivityTime': '1684104401000',
        'level': 85,
        'lifetimeSeasonScore': '731008',
        'localTimeZoneOffsetMinutes': 420,
        'name': 'Mar Trepodi',
        'playerId': 'cRdX7yGvS-eKfyDxAAgaYw',
        'playerRating': {...},
        'profileStat': [...],
        'pvpProfile': [...],
        'rosterUnit': [...],
        'seasonStatus': [...],
        'selectedPlayerPortrait': {...},
        'selectedPlayerTitle': {...},
        'unlockedPlayerPortrait': [...],
        'unlockedPlayerTitle': [...]
    }
"""
player_profile_data = comlink.get_player(allycode=314927874)

# We can extract a list of the characters in the player's roster
player_roster = player_profile_data['rosterUnit']

"""
# Each unit in a player's roster is a dictionary with entries for all attributes including skills, equipped mods
# and relics

>>> pprint.pprint(player['rosterUnit'][0], depth=1)
    {
        'currentLevel': 85,
        'currentRarity': 7,
         'currentTier': 13,
         'currentXp': 883025,
         'definitionId': 'MAGMATROOPER:SEVEN_STAR',
         'equipment': [],
         'equippedStatMod': [...],
         'equippedStatModOld': [],
         'id': 'xCNyaUFiR8OY3u5Qc-dC8Q',
         'promotionRecipeReference': '',
         'purchasedAbilityId': [],
         'relic': {...},
         'skill': [...],
         'unitStat': None
    }
"""