"""
Wrapper for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from .DataBuilder import DataBuilder, DataBuilderException, DataBuilderRuntimeError
from .StatCalc import StatCalc, StatCalcException, StatCalcRuntimeError
from .SwgohComlink import SwgohComlink
from .SwgohComlinkAsync import SwgohComlinkAsync
from .Utils import get_logger
from .const import DEFAULT_LOGGER_NAME

main_logger = get_logger(DEFAULT_LOGGER_NAME, log_to_file=True, log_level='DEBUG')
__version__ = '1.12.2'
main_logger.info('Starting SwgohComlink (%s)', __version__)

__all__ = [
    __version__,
    SwgohComlink,
    SwgohComlinkAsync,
    DataBuilder,
    DataBuilderException,
    DataBuilderRuntimeError,
    StatCalc,
    StatCalcException,
    StatCalcRuntimeError,
    const,
]
