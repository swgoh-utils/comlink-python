# coding=utf-8
"""
get_language_bundle.py
Sample script for retrieving a specific language bundle.
"""
import base64
import io
import zipfile

from swgoh_comlink import SwgohComlink

# Create a SwgohComlink instance
cl = SwgohComlink()

# Retrieve the German language strings (Default is to collect data as a base64 encoded compressed string
german_language_bundle = cl.get_localization(locale="ger_de")

# First decode the base64 string into the compressed object
german_language_bundle_decoded = base64.b64decode(german_language_bundle['localizationBundle'])

# Next create a ZipFile handler to interact with the compressed data object
zip_obj = zipfile.ZipFile(io.BytesIO(german_language_bundle_decoded))

"""
The compressed object will contain two elements. These can be seen using the namelist() method
of the zipfile package.

>>> zip_obj.namelist()
['Loc_GER_DE.txt', 'Loc_Key_Mapping.txt']
>>>
"""

# Extract the string information, decode it and split into individual lines
der_obj = zip_obj.read('Loc_GER_DE.txt')
der_obj_decoded = der_obj.decode('utf-8')
der_obj_lines = der_obj_decoded.splitlines()

# Each line has a key value and the corresponding text separated by a pipe ('|')
# To create a dictionary for easy mapping of strings from IDs used in game data collections,
#  loop through the lines, split on the '|' character and store the information in an empty dict
der_str_lookup = {}
for line in der_obj_lines:
    key, value = line.split('|')
    der_str_lookup[key] = value
