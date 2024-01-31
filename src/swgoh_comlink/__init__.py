# from .DataBuilder import DataBuilder
# from .StatCalc import StatCalc
from functools import wraps
from typing import Callable

from .SwgohComlink import SwgohComlink
# from .SwgohComlinkAsync import SwgohComlinkAsync
# from .Utils import *
from .version import __version__

version = __version__

__all__ = [
    'SwgohComlink',
    'SwgohComlinkAsync',
    'DataBuilder',
    'StatCalc',
    'Utils',
    'version',
    'param_alias',
]


def param_alias(param: str, alias: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Callable:
            if alias in kwargs:
                kwargs[param] = kwargs.pop(alias)
            return func(*args, **kwargs)

        return wrapper

    return decorator
