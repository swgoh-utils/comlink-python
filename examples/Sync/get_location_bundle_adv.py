"""
get_location_bundle_adv.py
Script to illustrate a more advanced and efficient usage of the swgoh_comlink
library to collect and parse the localization bundle.
"""

import base64
import io
import json
import os
import zipfile
from pathlib import Path

from swgoh_comlink import SwgohComlink

# Get the directory path of the current script
_PATH_ROOT = Path(__file__).resolve().parent

# Set the destination directory for the localization bundle files
_LANG_DIR = _PATH_ROOT / "data" / "languages"

# Make sure the destination directory exists
Path(_LANG_DIR).mkdir(parents=True, exist_ok=True)

# Set the Comlink host and port from environment variables or default to localhost:3000
COMLINK_HOST = os.environ.get("COMLINK_HOST") or "localhost"
COMLINK_PORT = os.environ.get("COMLINK_PORT") or 3000

print("Initializing Comlink [%s:%s] ...", COMLINK_HOST, COMLINK_PORT)
comlink = SwgohComlink(host=COMLINK_HOST, port=COMLINK_PORT)


def parse_loc_zip(
    zf: zipfile.ZipFile,
    output_dir: str | Path = ".",
    delimiter: str = "|",
    encoding: str = "utf-8",
) -> None:
    """
    Parses the content of a zip file containing delimited text files, transforms the data into a
    key-value JSON structure, and saves the result to specified output files.

    Arguments:
        zf (zipfile.ZipFile): The zip file object to be parsed.
        output_dir (str | Path): The directory where the parsed JSON files will be saved. Defaults to
            the current directory.
        delimiter (str): The character used to separate keys and values in the text files.
            Defaults to "|".
        encoding (str): The encoding used to read the text files. Defaults to "utf-8".

    Raises:
        OSError: If there is an error in creating the output directory or writing the output files.
        KeyError: If a delimited text file contains invalid key-value pairs without the delimiter.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for info in zf.infolist():
        if info.is_dir():
            continue

        # Create the output file name based on the information from the zip file entry
        output_path = output_dir / Path(info.filename).with_suffix(".json").name

        # Initialize an empty dictionary to store the key-value pairs
        result = {}

        # Process the zip file entry as a stream to conserve memory and extract the delimited text
        with zf.open(info) as raw, io.TextIOWrapper(raw, encoding=encoding) as stream:
            for line in stream:
                if line.startswith("#"):
                    continue
                # Use partition() instead of split() to split the line into key and value
                key, sep, value = line.rstrip("\r\n").partition(delimiter)
                # Only store the key-value pair if the delimiter is present
                if sep:
                    # Note: many of the "values" contain BBCode style formatting directives
                    #       that can be stripped or converted before storing them. See
                    #       `swgoh_comlink.helpers.parse_swgoh_string` for a parser that
                    #       emits plain text, Discord, terminal ANSI, or HTML output.
                    result[key] = value

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)


if __name__ == "__main__":
    print("Fetching latest game data version from Comlink")
    game_data_versions = comlink.get_latest_game_data_version()
    remote_lang = game_data_versions["language"]

    print("Fetching localization bundle (id=%s)", remote_lang)
    location_bundle = comlink.get_localization_bundle(
        localization_id=remote_lang,
    )

    loc_bundle_decoded = base64.b64decode(location_bundle["localizationBundle"])

    parse_loc_zip(zipfile.ZipFile(io.BytesIO(loc_bundle_decoded)), _LANG_DIR)
    print("Localization bundle parsed to %s", _LANG_DIR)
