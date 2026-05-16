# coding=utf-8
"""One-shot cassette recorder.

Hits a configured comlink instance and writes each endpoint response to
``benchmarks/v3/fixtures/<name>.json.gz``. Run this once per
:doc:`regeneration policy <fixtures/README>`.

Configuration via environment variables (all required unless marked optional):

    COMLINK_URL              Base URL of the comlink HTTP service.
                             e.g. ``http://localhost:3000``
    COMLINK_STATS_URL        Base URL of the stats sub-service.
                             [optional; defaults to <COMLINK_URL host>:3223]
    COMLINK_ACCESS_KEY       HMAC access key. [optional; no auth if unset]
    COMLINK_SECRET_KEY       HMAC secret key. [optional; required if access set]
    SMALL_ROSTER_ALLYCODE    9-digit ally code, ~50 unit roster.
    LARGE_ROSTER_ALLYCODE    9-digit ally code, ~250 unit roster.
    GUILD_ID                 Guild ID to record (use the guild of one of the
                             ally codes above so the cassette is internally
                             consistent).

Usage::

    COMLINK_URL=http://localhost:3000 \\
    SMALL_ROSTER_ALLYCODE=123456789 \\
    LARGE_ROSTER_ALLYCODE=987654321 \\
    GUILD_ID=abc123 \\
    uv run python -m benchmarks.v3._record

Records are written atomically (write to ``*.tmp``, then ``rename``) so an
interrupted run never leaves a half-written cassette.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from benchmarks.v3._harness import FIXTURES_DIR


@dataclass(frozen=True)
class Recording:
    """One cassette to capture: filename stem + the call that produces it."""

    name: str
    """Cassette filename without the ``.json.gz`` extension."""

    fetch: Callable[[Any], Any]
    """Callable taking a ``SwgohComlink`` and returning the JSON-able payload."""

    description: str


# ── Config ──────────────────────────────────────────────────────────────────


def _require_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        sys.stderr.write(f"error: ${name} is required. See benchmarks/v3/_record.py docstring.\n")
        sys.exit(2)
    return val


def _build_client() -> Any:
    """Construct a v2 ``SwgohComlink`` from environment."""
    # Imported lazily so that just *importing* this module doesn't drag httpx in.
    from swgoh_comlink import SwgohComlink

    url = _require_env("COMLINK_URL")
    kwargs: dict[str, Any] = {"url": url}
    stats_url = os.environ.get("COMLINK_STATS_URL")
    if stats_url:
        kwargs["stats_url"] = stats_url
    access_key = os.environ.get("COMLINK_ACCESS_KEY")
    secret_key = os.environ.get("COMLINK_SECRET_KEY")
    if access_key and secret_key:
        kwargs["access_key"] = access_key
        kwargs["secret_key"] = secret_key
    return SwgohComlink(**kwargs)


# ── Recording catalog ───────────────────────────────────────────────────────


def _build_recordings() -> list[Recording]:
    small = _require_env("SMALL_ROSTER_ALLYCODE")
    large = _require_env("LARGE_ROSTER_ALLYCODE")
    guild_id = _require_env("GUILD_ID")

    return [
        Recording(
            name="metadata",
            fetch=lambda c: c.get_game_metadata(),
            description="/metadata — version-keying tests need this",
        ),
        Recording(
            name="player_small",
            fetch=lambda c: c.get_player(allycode=small),
            description=f"/player for ally code {small} (small roster)",
        ),
        Recording(
            name="player_large",
            fetch=lambda c: c.get_player(allycode=large),
            description=f"/player for ally code {large} (large roster)",
        ),
        Recording(
            name="guild",
            fetch=lambda c: c.get_guild(guild_id=guild_id),
            description=f"/guild for guild ID {guild_id}",
        ),
        Recording(
            name="data",
            fetch=lambda c: c.get_game_data(request_segment=0),
            description="/data full dump (request_segment=0)",
        ),
        Recording(
            name="localization_eng_us",
            fetch=lambda c: c.get_localization(locale="ENG_US", unzip=True),
            description="/localization for ENG_US locale (decompressed payload)",
        ),
        Recording(
            name="leaderboard",
            fetch=lambda c: c.get_leaderboard(leaderboard_type=6, league="kyber", division=1),
            description="/getLeaderboard type=6 (global), Kyber league div 1",
        ),
    ]


# ── Capture ─────────────────────────────────────────────────────────────────


def _write_cassette(payload: Any, name: str) -> Path:
    """Serialize *payload* to ``fixtures/<name>.json.gz`` atomically."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    dest = FIXTURES_DIR / f"{name}.json.gz"
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    with gzip.open(tmp, "wb", compresslevel=6) as fh:
        fh.write(body)
    tmp.replace(dest)
    return dest


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Record comlink cassettes for the v3 benchmark harness.")
    p.add_argument(
        "--only",
        metavar="NAME[,NAME...]",
        help=(
            "Comma-separated cassette names to record (e.g. 'player_small' or "
            "'player_small,guild'). Omit to record all cassettes. Use this for "
            "surgical regen when only one or two fixtures need refreshing."
        ),
    )
    return p.parse_args()


def main() -> int:
    """Record cassettes from :func:`_build_recordings`.

    With no ``--only`` filter, records every cassette. Returns exit code
    ``0`` on full success, ``1`` if any requested cassette failed (others
    still attempted), ``2`` if ``--only`` names an unknown cassette.
    """
    args = _parse_args()
    client = _build_client()
    recordings = _build_recordings()

    if args.only:
        wanted = {n.strip() for n in args.only.split(",") if n.strip()}
        known = {r.name for r in recordings}
        unknown = wanted - known
        if unknown:
            sys.stderr.write(
                f"error: --only references unknown cassette(s): {sorted(unknown)}. Known: {sorted(known)}\n"
            )
            return 2
        recordings = [r for r in recordings if r.name in wanted]

    failures: list[tuple[str, str]] = []

    sys.stderr.write(f"Recording {len(recordings)} cassette(s) → {FIXTURES_DIR}\n")
    for rec in recordings:
        sys.stderr.write(f"  {rec.name:24s} {rec.description}\n")
        try:
            data = rec.fetch(client)
        except Exception as exc:  # noqa: BLE001 — recorder is best-effort by design
            failures.append((rec.name, repr(exc)))
            sys.stderr.write(f"    FAILED: {exc}\n")
            continue
        dest = _write_cassette(data, rec.name)
        size_kib = dest.stat().st_size / 1024
        sys.stderr.write(f"    wrote {size_kib:.1f} KiB → {dest.name}\n")

    if failures:
        sys.stderr.write(f"\n{len(failures)} cassette(s) failed:\n")
        for name, err in failures:
            sys.stderr.write(f"  {name}: {err}\n")
        return 1

    sys.stderr.write("\nDone. Re-run `bench_baseline.py` to refresh the baseline.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
