"""
get_location_bundle.py
Script to illustrate the basic usage of the async swgoh_comlink wrapper library
"""

import asyncio
import base64
import io
import zipfile

# import the SwgohComlinkAsync class from the swgoh_comlink module
from swgoh_comlink import SwgohComlinkAsync


async def main():
    # create an instance of a SwgohComlinkAsync object
    async with SwgohComlinkAsync() as comlink:
        """
        # Call the get_localization_bundle() method of the SwgohComlinkAsync instance to retrieve the language
        # localization bundle.
        """
        # Get the current game version
        game_data_versions = await comlink.get_latest_game_data_version()

        # Get the language bundle using the latest game data language version
        # By default, Comlink compresses the data and encodes it into a BASE64 string for smaller payload and
        # faster delivery. The result is a string value that must be decoded before using.
        location_bundle = await comlink.get_localization_bundle(localization_id=game_data_versions["language"])

        # Decode the Base64 result
        loc_bundle_decoded = base64.b64decode(location_bundle["localizationBundle"])

        # Create a zipfile object to access the compressed content
        zip_obj = zipfile.ZipFile(io.BytesIO(loc_bundle_decoded))

        # Get a list of language elements contained in the zip data
        """
        Sample output:

        ['Loc_CHS_CN.txt', 'Loc_CHT_CN.txt', 'Loc_ENG_US.txt', 'Loc_FRE_FR.txt', 'Loc_GER_DE.txt',
            'Loc_IND_ID.txt', 'Loc_ITA_IT.txt', 'Loc_JPN_JP.txt', 'Loc_Key_Mapping.txt', 'Loc_KOR_KR.txt',
            'Loc_POR_BR.txt', 'Loc_RUS_RU.txt', 'Loc_SPA_XM.txt', 'Loc_THA_TH.txt', 'Loc_TUR_TR.txt']

        """
        lang_files = zip_obj.namelist()

        # Extract the English bundle for use. Note this returns a byte array. Decode if you want to work with
        # it as a string. You could also use the various other zipfile methods to extract all files to disk
        # (see https://docs.python.org/3/library/zipfile.html for more details), or loop through the namelist()
        # output and select only specific languages you are interested in.
        eng_obj = zip_obj.read("Loc_ENG_US.txt")

        # Decode to string then split into individual lines
        eng_obj_decoded = eng_obj.decode("utf-8")
        eng_obj_lines = eng_obj_decoded.splitlines()

        """
        Alternatively, if you elected to have Comlink send an unzipped response, the result is a dictionary
        containing keys for all of the language files (similar to the namelist() output from the zipfile method
        above.
        """
        location_bundle_unzipped = await comlink.get_localization_bundle(
            localization_id=game_data_versions["language"], unzip=True
        )

        """
        Each key of the result dictionary is a string that can be split into individual lines, or written to files.

        >>> location_bundle_unzipped.keys()
        dict_keys(['Loc_CHS_CN.txt', 'Loc_CHT_CN.txt', 'Loc_ENG_US.txt', 'Loc_FRE_FR.txt', 'Loc_GER_DE.txt',
        'Loc_IND_ID.txt', 'Loc_ITA_IT.txt', 'Loc_JPN_JP.txt', 'Loc_Key_Mapping.txt', 'Loc_KOR_KR.txt',
        'Loc_POR_BR.txt', 'Loc_RUS_RU.txt', 'Loc_SPA_XM.txt', 'Loc_THA_TH.txt', 'Loc_TUR_TR.txt'])

        Depending on the speed of your connection and other resource factors, the time needed to retrieve the
        localization data can be significantly higher for unzipped versus zipped.
        """


asyncio.run(main())
