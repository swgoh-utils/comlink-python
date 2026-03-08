# coding=utf-8
"""
get_game_data.py
Sample script to retrieve game data from the SWGoH game servers using the async client
"""

import asyncio

from swgoh_comlink import SwgohComlinkAsync
from swgoh_comlink.helpers import Constants


async def main():
    # Create an instance of SwgohComlinkAsync
    async with SwgohComlinkAsync() as cl:
        # Retrieve all of the available game data
        game_data = await cl.get_game_data(items="ALL")

        # Alternatively, retrieve only the unit information collection
        unit_data = await cl.get_game_data(items="UnitDefinitions")

        # This is the same call as above but without the PVE units
        unit_data_no_pve = await cl.get_game_data(items="UnitDefinitions", include_pve_units=False)

        # If you want to get more than one collection at once, simply combine the collection values
        game_data_segments_1_and_2 = await cl.get_game_data(items=Constants.Segment1 + Constants.Segment2)

        # Note that the 'items' and legacy 'request_segment' parameters are mutually exclusive.
        # If you supply arguments for both, the `request_segment` argument will be ignored in favor
        # of the 'items' argument.


asyncio.run(main())
