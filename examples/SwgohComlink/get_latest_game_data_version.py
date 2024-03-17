"""
get_latest_game_data_version.py
Script to illustrate the basic usage of the comlink_python wrapper library
"""
# import the SwgohComlink class from the comlink_python module
from swgoh_comlink import SwgohComlink

# create an instance of a SwgohComlink object
comlink = SwgohComlink()

"""
# Call the get_latest_game_data_version() helper function of the SwgohComlink instance to retrieve a simple
# dictionary containing the current game data and language bundle version strings.

The result is a dictionary with the following two keys:

{'game': '0.32.1:B4nCO_VUS8-DvSQOrgTm0w', 'language': '-kVUobbdRleiHUoQu_DA2Q'}

"""
current_game_version = comlink.get_latest_game_data_version()

print(f"{current_game_version}")
# For those that are averse to typing long descriptive function names, there is an alias that can be used
# which is much shorter, getVersion()

current_versions = comlink.getVersion()
print(f"{current_versions}")
