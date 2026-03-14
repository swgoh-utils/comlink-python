import os

from swgoh_comlink import SwgohComlink


def build_comlink() -> SwgohComlink:
    return SwgohComlink(
        url=os.getenv("COMLINK_URL", "http://localhost:3000"),
        stats_url=os.getenv("COMLINK_STATS_URL", "http://localhost:3223"),
        access_key=os.getenv("ACCESS_KEY"),
        secret_key=os.getenv("SECRET_KEY"),
    )


def test_allycode(default: int = 245866537) -> int:
    return int(os.getenv("TEST_ALLYCODE", str(default)))
