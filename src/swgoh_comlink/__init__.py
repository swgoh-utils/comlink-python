"""
Wrapper for swgoh-comlink (https://github.com/swgoh-utils/swgoh-comlink)
"""
import swgoh_comlink.Utils
from .SwgohComlink import *

main_logger = swgoh_comlink.Utils.get_logger('SwgohComlink', log_to_file=True, logfile_name='SwgohComlink.log')
version = swgoh_comlink.Utils.get_version()
main_logger.info('Starting SwgohComlink (%s)', version)
