"""
Wrapper for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
from .SwgohComlink import SwgohComlink
from .SwgohComlinkAsync import SwgohComlinkAsync
from .Utils import get_logger

main_logger = get_logger(__name__, log_to_file=True, log_level='DEBUG')
__version__ = '1.13.0_alpha_7'
main_logger.info('Starting SwgohComlink (%s)', __version__)

__all__ = [
    __version__,
    SwgohComlink,
    SwgohComlinkAsync,
]
