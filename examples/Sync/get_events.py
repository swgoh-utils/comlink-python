"""
get_events.py
Sample script to get events from Comlink
"""

from datetime import datetime, timezone
from typing import Union

from swgoh_comlink import SwgohComlink


def convert_time(timestamp: Union[int, str]) -> str:
    """
    Convert unix timestamp to human-readable string
    :param timestamp: integer or string representing a unix timestamp value
    :return: str
    """

    if not (isinstance(timestamp, str) or isinstance(timestamp, int)):
        return f'Invalid argument {timestamp}, type( {type(timestamp)} ). Expecting type str or int.'

    if len(str(timestamp)) > 10:
        # timestamp is in milliseconds
        timestamp = int(timestamp)
        timestamp /= 1000

    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


# Create instance of SwgohComlink using default localhost settings
comlink = SwgohComlink()

# Get all available currently available events from game servers
events = comlink.get_events()

"""
The call above returns a single element dictionary with a key name of 'gameEvent'. The value of this element is a
list of all the available game events at that time.
"""

if 'gameEvent' not in events:
    print(f'Unexpected response from game server, check your internet connection. {events}')
    exit(1)

# Loop through the events and print the ID, status relevant time entries for each occurrence
for event in events['gameEvent']:
    print(f'{event["id"]=}, {event["status"]=}')
    instances = event['instance']
    for instance in instances:
        display_start = convert_time(instance['displayStartTime'])
        display_end = convert_time(instance['displayEndTime'])
        start_time = convert_time(instance['startTime'])
        reward_time = convert_time(instance['rewardTime'])
        print(f'\t{display_start=}')
        print(f'\t{display_end=}')
        print(f'\t{start_time=}')
        print(f'\t{reward_time=}')
