"""The async -> sync generator in ``.github/scripts/unasync.py``, and the sync client it keeps current."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "unasync.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("unasync_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


unasync = _load()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("async def f():\n    pass\n", "def f():\n    pass\n", id="async-def"),
        pytest.param("async with a as b:\n    pass\n", "with a as b:\n    pass\n", id="async-with"),
        pytest.param("async for x in y:\n    pass\n", "for x in y:\n    pass\n", id="async-for"),
        pytest.param("x = await f(1)\n", "x = f(1)\n", id="await"),
        pytest.param("return await self._post(a, b)\n", "return self._post(a, b)\n", id="await-return"),
    ],
)
def test_async_keywords_are_dropped(source: str, expected: str) -> None:
    assert unasync.unasync_source(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("v = (await self.get()).version\n", "v = self.get().version\n", id="attribute-on-awaited-call"),
        pytest.param("v = (await self.get(x=1))[0]\n", "v = self.get(x=1)[0]\n", id="subscript-on-awaited-call"),
        pytest.param("return (await f())\n", "return f()\n", id="after-keyword"),
        pytest.param("y = g(await f())\n", "y = g(f())\n", id="call-paren-kept"),
        # Not a single primary: dropping the group would change precedence (x * a + b).
        pytest.param("y = x * (await a + b)\n", "y = x * (a + b)\n", id="operator-group-kept"),
        pytest.param("y = (await a) if c else d\n", "y = a if c else d\n", id="name-only"),
    ],
)
def test_grouping_parens_go_only_around_a_single_primary(source: str, expected: str) -> None:
    assert unasync.unasync_source(source) == expected


def test_names_dotted_names_and_imports_are_renamed() -> None:
    source = (
        "import asyncio\n"
        "class SwgohComlinkAsync(Base):\n"
        "    async def __aenter__(self): ...\n"
        "    async def aclose(self):\n"
        "        self._lock = asyncio.Lock()\n"
        "        await self.client.aclose()\n"
        "        client: httpx.AsyncClient\n"
        "        await _retry._async_sleep(1)\n"
        "        async for chunk in r.aiter_bytes(): ...\n"
    )
    assert unasync.unasync_source(source) == (
        "import threading\n"
        "class SwgohComlink(Base):\n"
        "    def __enter__(self): ...\n"
        "    def close(self):\n"
        "        self._lock = threading.Lock()\n"
        "        self.client.close()\n"
        "        client: httpx.Client\n"
        "        _retry._sleep(1)\n"
        "        for chunk in r.iter_bytes(): ...\n"
    )


def test_asyncio_names_other_than_lock_are_left_for_review() -> None:
    """Only ``asyncio.Lock`` has a known sync twin; anything else must stay visible in the generated file."""
    assert unasync.unasync_source("except asyncio.CancelledError:\n") == "except asyncio.CancelledError:\n"


def test_docstrings_and_comments_get_names_and_example_code_only() -> None:
    source = (
        "def f():\n"
        '    """Asynchronous interface; see :class:`SwgohComlinkAsync` and :meth:`aclose`.\n'
        "\n"
        "    Example::\n"
        "\n"
        "        async with SwgohComlinkAsync() as comlink:\n"
        "            player = await comlink.get_player()\n"
        "\n"
        "    The async client and asynchronous callers are described as written.\n"
        '    """\n'
        "    # SwgohComlinkAsync keeps one pool\n"
    )
    assert unasync.unasync_source(source) == (
        "def f():\n"
        '    """Synchronous interface; see :class:`SwgohComlink` and :meth:`close`.\n'
        "\n"
        "    Example::\n"
        "\n"
        "        with SwgohComlink() as comlink:\n"
        "            player = comlink.get_player()\n"
        "\n"
        "    The async client and asynchronous callers are described as written.\n"
        '    """\n'
        "    # SwgohComlink keeps one pool\n"
    )


def test_names_that_merely_contain_a_renamed_name_are_untouched() -> None:
    source = "SwgohComlinkAsyncFactory = aclose_all\n"
    assert unasync.unasync_source(source) == source


@pytest.mark.skipif(shutil.which("ruff") is None, reason="ruff formats the generated file; the lint job runs this")
def test_committed_sync_clients_are_what_the_async_ones_generate() -> None:
    for source_name, target_name in unasync.FILES:
        target = unasync.PACKAGE / target_name
        assert target.read_text(encoding="utf-8") == unasync.generate(unasync.PACKAGE / source_name, target), (
            f"{target_name} is out of date or was edited by hand: run `uv run python .github/scripts/unasync.py`."
        )
