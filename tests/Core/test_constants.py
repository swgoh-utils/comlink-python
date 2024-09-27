import logging

import swgoh_comlink.constants as constants


def test__get_logger_with_no_name():
    logger: logging.Logger = constants._get_new_logger(name=constants.NotSet)
    assert logger.name == constants._DEFAULT_LOGGER_NAME


def test_get_logger_with_default_null_handler():
    logger: logging.Logger = constants.get_logger(name="test_logger", default_logger=False)
    for handler in logger.handlers:
        if isinstance(handler, logging.NullHandler):
            assert True
