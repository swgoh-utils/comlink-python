# coding=utf-8
"""
File containing test configurations for the SwgohComlinkBase class
"""
import pytest

from swgoh_comlink._base import SwgohComlinkBase


def test_no_instance():
    with pytest.raises(TypeError):
        SwgohComlinkBase()
