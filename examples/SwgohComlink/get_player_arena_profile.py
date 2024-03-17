"""
get_player_arena_profile.py
Script to illustrate the basic usage of the comlink_python wrapper library
"""

# Place module imports below this line
from swgoh_comlink import SwgohComlink

# create an instance of a SwgohComlink object
comlink = SwgohComlink()

# Get a player's arena profile information
player_arena_profile = comlink.get_player_arena(allycode=314927874)
"""
The result is a dictionary containing PvP arena as well as left over data from the original GAC
scoring system. That GAC data is no longer valid and should be ignored.

    {
        'allyCode': '314927874',
         'level': 85,
         'lifetimeSeasonScore': '731008',
         'localTimeZoneOffsetMinutes': 420,
         'name': 'Mar Trepodi',
         'playerId': 'cRdX7yGvS-eKfyDxAAgaYw',
         'playerRating': {
            'playerRankStatus': {...},
            'playerSkillRating': {...}
            },
         'pvpProfile': [{...}, {...}]
     }

If you only need basic stats and not the full arena squad unit information, you can provide the
"player_details_only=True" argument.
 """

# Get a player's arena profile information
player_arena_profile_brief = comlink.get_player_arena(
    allycode=314927874, player_details_only=True
)
