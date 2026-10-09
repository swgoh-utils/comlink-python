# coding=utf-8
"""
get_game_data.py
Sample script to retrieve game data from the SWGoH game servers using the async client
"""

import asyncio

from swgoh_comlink import SwgohComlinkAsync
from swgoh_comlink.helpers import Constants, DataItems


async def main():
    # Create an instance of SwgohComlinkAsync
    async with SwgohComlinkAsync() as cl:
        # Retrieve all of the available game data
        game_data = await cl.get_game_data(items="ALL")

        # Retrieve a single collection. Requesting only the collections you need is much
        # faster and uses less memory than requesting whole segments.
        units = await cl.get_game_data(items=DataItems.UNITS)

        # The same call without the PVE units
        units_no_pve = await cl.get_game_data(items=DataItems.UNITS, include_pve_units=False)

        # Combine collections with `|` (not `+`, which breaks for aliased members)
        skill_equipment = await cl.get_game_data(items=DataItems.SKILL | DataItems.EQUIPMENT)

        # Retrieve whole segments (the collections returned by the legacy request_segment= calls)
        segment1_data = await cl.get_game_data(items=DataItems.SEGMENT1)
        game_data_segments_1_and_2 = await cl.get_game_data(items=Constants.Segment1 | Constants.Segment2)

        # Note that the 'items' and legacy 'request_segment' parameters are mutually exclusive.
        # If you supply arguments for both, the `request_segment` argument will be ignored in favor
        # of the 'items' argument.


asyncio.run(main())
