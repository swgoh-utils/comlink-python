# coding=utf-8
"""
healthcheck_and_retry.py — v3-only ergonomics

Demonstrates two v3 additions that have no v2 analogue:

  1. ``client.healthcheck(timeout=5.0)`` — startup probe; returns
     bool. Use it to fail fast on unreachable comlink instances
     before a long-running process settles into its main loop.

  2. ``profile="bot"`` + ``retry=RetryPolicy(...)`` — a connection-pool
     preset tuned for long-lived processes, plus an opt-in retry policy
     that rides out rate refusals and HTTP 503 from comlink. Retries are
     off by default: without ``retry=`` a call makes exactly one attempt.

The typed client and dict client both support these; this example
uses the typed import for consistency with the rest of
``examples/typed/Sync/``.
"""

import sys
import time

from swgoh_comlink import RetryPolicy
from swgoh_comlink.exceptions import SwgohComlinkException
from swgoh_comlink.typed import SwgohComlink

# ── Healthcheck before settling into the main loop ──────────────────────────
#
# Returns True if comlink is reachable + responsive within `timeout`
# seconds; False otherwise. Cheap — single HTTP call to /enums.
probe_client = SwgohComlink(url="http://localhost:3200")
if not probe_client.healthcheck(timeout=5.0):
    print("comlink unreachable at http://localhost:3200; aborting", file=sys.stderr)
    sys.exit(1)
print("comlink healthcheck OK")

# ── Production-leaning client config ────────────────────────────────────────
#
# `profile="bot"` selects:
#   - httpx keep-alive 120 s + larger connection pool
#
# `retry=RetryPolicy(attempts=3, min_interval=0.4)` opts in to retrying
# rate refusals (HTTP 429 / "Rate exceeded!") and HTTP 503 up to 3 attempts
# in total, honouring `Retry-After` (otherwise 5, 10, 20 ... seconds of
# back-off plus jitter), and spaces calls to the same endpoint at least
# 0.4 s apart. Any other error is raised at once.
#
# Connection-pool profiles available today:
#   - "default" — httpx defaults; suits CLI / scripts
#   - "bot"     — recommended for long-lived bots / services
#   - "bulk"    — large pool for high-fanout batch jobs
client = SwgohComlink(
    url="http://localhost:3200",
    profile="bot",
    retry=RetryPolicy(attempts=3, min_interval=0.4),
)

# ── Main loop demonstrating retry surface ───────────────────────────────────
#
# In a real bot you'd iterate forever with a sleep between ticks.
# This example does a fixed number of fetches so it terminates.
for tick in range(3):
    try:
        player = client.get_player(allycode=314927874)
        print(f"tick {tick}: {player.name} (level {player.level})")
    except SwgohComlinkException as e:
        # Rate refusals and HTTP 503 reaching here were already retried per
        # the RetryPolicy; other errors (e.g. a rejected request) are raised
        # at once as typed SwgohComlinkHTTPError subclasses.
        print(f"tick {tick}: failed after retries — {type(e).__name__}: {e}", file=sys.stderr)
    time.sleep(1.0)

print("done")
