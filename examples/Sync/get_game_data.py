# coding=utf-8
"""
get_game_data.py
Sample script to retrieve game data from the SWGoH game servers
"""

from swgoh_comlink import SwgohComlink
from swgoh_comlink.helpers import Constants, DataItems

# Create an instance of SwgohComlink
cl = SwgohComlink()

# Retrieve all of the available game data
game_data = cl.get_game_data(items="ALL")

# Retrieve a single collection. Requesting only the collections you need is much
# faster and uses less memory than requesting whole segments.
units = cl.get_game_data(items=DataItems.UNITS)

# The same call without the PVE units
units_no_pve = cl.get_game_data(items=DataItems.UNITS, include_pve_units=False)

# Combine collections with `|` (not `+`, which breaks for aliased members)
skill_equipment = cl.get_game_data(items=DataItems.SKILL | DataItems.EQUIPMENT)

# Retrieve whole segments (the collections returned by the legacy request_segment= calls)
segment1_data = cl.get_game_data(items=DataItems.SEGMENT1)
game_data_segments_1_and_2 = cl.get_game_data(items=Constants.Segment1 | Constants.Segment2)

# Note that the 'items' and legacy 'request_segment' parameters are mutually exclusive.
# If you supply arguments for both, the `request_segment` argument will be ignored in favor
# of the 'items' argument.
