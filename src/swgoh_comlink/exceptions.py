# coding=utf-8
"""
Collection of all custom exceptions for swgoh_comlink
"""
from swgoh_comlink.constants import get_logger

logger = get_logger()

__all__ = [
    'ComlinkValueError',
    'StatValueError',
    'StatTypeError',
    'StatCalcException',
    'StatCalcRuntimeError',
    'StatCalcValueError',
    'DataBuilderValueError',
    'DataBuilderRuntimeError',
    'DataBuilderException',
]


class ComlinkValueError(ValueError):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise ValueError(err_msg)


class StatValueError(ValueError):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise ValueError(err_msg)


class StatTypeError(TypeError):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise TypeError(err_msg)


class StatCalcException(Exception):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise Exception(err_msg)


class StatCalcRuntimeError(RuntimeError):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise RuntimeError(err_msg)


class StatCalcValueError(ValueError):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise ValueError(err_msg)


class DataBuilderException(Exception):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise Exception(err_msg)


class DataBuilderRuntimeError(RuntimeError):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise RuntimeError(err_msg)


class DataBuilderValueError(ValueError):

    def __init__(self, err_msg: str):
        logger.error(err_msg)
        raise ValueError(err_msg)
