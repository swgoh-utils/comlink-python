import os

from swgoh_comlink import SwgohComlink
from swgoh_comlink.utils import get_function_name

secure_comlink = SwgohComlink(port=3010, access_key="public_access_key", secret_key="private_secret_key")


def test_access_and_secret_keys(allycode):
    secure_comlink.logger.debug(f"** Starting {get_function_name()} with {allycode=}")
    player = secure_comlink.get_player(allycode)
    assert 'name' in player.keys()


def test_access_and_secret_keys_from_env():
    os.environ['ACCESS_KEY'] = 'public_env_access_key'
    os.environ['SECRET_KEY'] = 'private_env_secret_key'
    test_comlink = SwgohComlink()
    assert test_comlink.access_key == 'public_env_access_key'
    assert test_comlink.secret_key == '<HIDDEN>'


def test_get_access_key():
    secure_comlink.logger.debug(f"** Starting {get_function_name()}")
    assert secure_comlink.access_key == "public_access_key"
    secure_comlink.logger.debug(f"** Completed {get_function_name()} - "
                                f"secure_comlink.access_key == 'public_access_key' is "
                                f"{secure_comlink.access_key == 'public_access_key'}")


def test_get_secret_key():
    secure_comlink.logger.debug(f"** Starting {get_function_name()}")
    assert secure_comlink.secret_key == "<HIDDEN>"
    secure_comlink.logger.debug(f"** Completed {get_function_name()} - "
                                f"secure_comlink.secret_key == '<HIDDEN>' is "
                                f"{secure_comlink.secret_key == '<HIDDEN>'}")
