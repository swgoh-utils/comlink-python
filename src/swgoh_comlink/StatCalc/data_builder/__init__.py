"""GameDataBuilder — build StatCalc game data from a running Comlink service.

Provides sync and async builders that fetch raw game data collections via
SwgohComlink / SwgohComlinkAsync and transform them into the dict format
expected by StatCalc.set_game_data().
"""

from .builder import GameDataBuilder
from .builder_async import GameDataBuilderAsync

__all__ = ["GameDataBuilder", "GameDataBuilderAsync"]
