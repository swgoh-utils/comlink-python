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

        # Retrieve a single segment. The Comlink server validates `items` against its
        # GameDataItemsEnum and accepts the Segment1-4 aggregates; raw single-collection
        # bit values (e.g. DataItems.UNITS) may be rejected with an HTTP 400.
        segment1_data = await cl.get_game_data(items=DataItems.SEGMENT1)

        # The same call without the PVE units
        segment1_no_pve = await cl.get_game_data(items=DataItems.SEGMENT1, include_pve_units=False)

        # Combine segments to request multiple collections at once
        game_data_segments_1_and_2 = await cl.get_game_data(items=Constants.Segment1 + Constants.Segment2)

        # Note that the 'items' and legacy 'request_segment' parameters are mutually exclusive.
        # If you supply arguments for both, the `request_segment` argument will be ignored in favor
        # of the 'items' argument.


asyncio.run(main())
