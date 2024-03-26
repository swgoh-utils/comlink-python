"""
async_get_events.py
Sample script to get events from Comlink
"""

import asyncio
from datetime import datetime, UTC
from typing import Any

from swgoh_comlink import SwgohComlinkAsync


def convert_time(timestamp: Any) -> str:
    """
    Convert unix timestamp to human-readable string
    :param timestamp: integer or string representing a unix timestamp value
    :return: str
    """
    if not (isinstance(timestamp, str) or isinstance(timestamp, int)):
        return f"Invalid argument {timestamp}, type( {type(timestamp)} ). Expecting type str or int."
    if len(str(timestamp)) > 10:
        # timestamp is in milliseconds
        timestamp = int(timestamp)
        timestamp /= 1000
    return datetime.fromtimestamp(int(timestamp), UTC).strftime("%Y-%m-%d %H:%M:%S")


"""
The call above returns a single element dictionary with a key name of 'gameEvent'. The value of this element is a
list of all the available game events at that time.
"""


async def main():
    """Main program code for getting SWG0H events and displaying each of them"""
    # Create instance of SwgohComlink
    comlink = SwgohComlinkAsync()
    # Get all available events
    events = await comlink.get_events()
    # Loop through the events and print the ID, status relevant time entries for each occurrence
    for event in events["gameEvent"]:
        print(f'{event["id"]=}, {event["status"]=}')
        instances = event["instance"]
        for instance in instances:
            display_start = convert_time(instance["displayStartTime"])
            display_end = convert_time(instance["displayEndTime"])
            start_time = convert_time(instance["startTime"])
            reward_time = convert_time(instance["rewardTime"])
            print(f"\t{display_start=}")
            print(f"\t{display_end=}")
            print(f"\t{start_time=}")
            print(f"\t{reward_time=}")
    await comlink.client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
