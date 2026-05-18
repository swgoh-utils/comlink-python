# coding=utf-8
"""Generate the four client variants from the manifest.

Run::

    uv run python -m swgoh_comlink._codegen.generate

Writes 4 files (sync/async × dict/typed). Runs ``ruff format`` on the
output so generator whitespace doesn't matter and formatting matches the
project standard.

A pre-commit hook + CI step run ``make generate && git diff --exit-code``
to refuse commits when the generator output diverges from the manifest.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .endpoints import ENDPOINTS

_HERE = Path(__file__).resolve().parent
_PKG_ROOT = _HERE.parent  # src/swgoh_comlink/

# (is_async, is_typed, output_path)
_OUTPUTS: tuple[tuple[bool, bool, Path], ...] = (
    (False, False, _PKG_ROOT / "swgoh_comlink.py"),
    (True, False, _PKG_ROOT / "swgoh_comlink_async.py"),
    (False, True, _PKG_ROOT / "typed" / "swgoh_comlink.py"),
    (True, True, _PKG_ROOT / "typed" / "swgoh_comlink_async.py"),
)


def main() -> int:
    env = Environment(
        loader=FileSystemLoader(_HERE / "templates"),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    tpl = env.get_template("client.py.jinja")

    written: list[Path] = []
    for is_async, is_typed, out_path in _OUTPUTS:
        rendered = tpl.render(
            endpoints=ENDPOINTS,
            is_async=is_async,
            is_typed=is_typed,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered)
        written.append(out_path)
        sys.stderr.write(f"  wrote {out_path.relative_to(_PKG_ROOT.parent.parent)}\n")

    # Format with ruff so generator whitespace doesn't matter.
    sys.stderr.write("  ruff format ...\n")
    result = subprocess.run(
        ["uv", "run", "ruff", "format", *(str(p) for p in written)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        return result.returncode

    sys.stderr.write(f"\nGenerated {len(written)} client files.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
