"""
get_guild.py
Sample script to get guild information from Comlink with custom logging
"""
import logging

from swgoh_comlink import SwgohComlink

# Create instance of SwgohComlink
comlink = SwgohComlink()

"""
Create a custom logging object with specific formatting
"""
logger = logging.getLogger('swgoh_comlink')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

"""
The get_guild() call requires a positional parameter 'guild_id'. The guild_id can be found in a guild member
player profile. In the example below, we'll make a call to the get_player() method first and then use the guild_id
from the response to call the get_guild() method.
"""
player = comlink.get_player(314927874)
guild = comlink.get_guild(player["guildId"])

guild_members = guild['member']
