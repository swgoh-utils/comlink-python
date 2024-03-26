"""
get_latest_game_data_version.py
Script to illustrate the basic usage of the comlink_python wrapper library
"""
import asyncio

# import the SwgohComlink class from the comlink_python module
from swgoh_comlink import SwgohComlinkAsync


async def main():
    """
    # Call the get_latest_game_data_version() helper function of the SwgohComlink instance to retrieve a simple
    # dictionary containing the current game data and language bundle version strings.

    The result is a dictionary with the following two keys:

    {'game': '0.32.1:B4nCO_VUS8-DvSQOrgTm0w', 'language': '-kVUobbdRleiHUoQu_DA2Q'}

    """
    # create an instance of a SwgohComlink object
    comlink = SwgohComlinkAsync()
    current_game_version = await comlink.get_latest_game_data_version()

    print(f"{current_game_version}")
    # For those that are averse to typing long descriptive function names, there is an alias that can be used
    # which is much shorter, getVersion()

    current_versions = await comlink.getVersion()
    print(f"{current_versions}")
    await comlink.client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
