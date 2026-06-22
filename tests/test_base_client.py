from typing import get_type_hints

import pytest
from typing_extensions import Self

from swgoh_comlink import SwgohComlink
from swgoh_comlink._base import SwgohComlinkBase


def test_base_class_new_typing():
    """Test that SwgohComlinkBase __new__ returns correct type."""
    type_hints = get_type_hints(obj=SwgohComlinkBase.__new__)
    assert type_hints.get("return") == Self


def test_base_class_instantiation():
    """Test that SwgohComlinkBase prevents direct instantiation."""
    with pytest.raises(TypeError, match="Only subclasses of 'SwgohComlinkBase' may be instantiated"):
        SwgohComlinkBase()

    class ChildSwgohClient(SwgohComlinkBase):
        pass

    child_instance = ChildSwgohClient()
    assert isinstance(child_instance, ChildSwgohClient)

    client = SwgohComlink()
    assert isinstance(client, SwgohComlink)
