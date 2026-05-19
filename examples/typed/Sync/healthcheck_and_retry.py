# coding=utf-8
"""
healthcheck_and_retry.py — v3-only ergonomics

Demonstrates two v3 additions that have no v2 analogue:

  1. ``client.healthcheck(timeout=5.0)`` — startup probe; returns
     bool. Use it to fail fast on unreachable comlink instances
     before a long-running process settles into its main loop.

  2. ``profile="bot"`` + ``max_retries=`` — selects a retry policy
     tuned for long-lived processes that need to ride out
     transient comlink hiccups. Backed by ``stamina>=24.3``.

The typed client and dict client both support these; this example
uses the typed import for consistency with the rest of
``examples/typed/Sync/``.
"""

import sys
import time

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
#   - retry on 5xx + transient httpx exceptions
#   - exponential back-off with jitter
#
# `max_retries=3` means up to 1 initial attempt + 3 retries before
# the request gives up + raises.
#
# Profiles available today:
#   - "default" — minimal retries, short keep-alive; suits CLI / scripts
#   - "bot"     — recommended for long-lived bots / services
#   - "cli"     — explicit short-lived profile (= "default" today)
client = SwgohComlink(
    url="http://localhost:3200",
    profile="bot",
    max_retries=3,
)

# ── Main loop demonstrating retry surface ───────────────────────────────────
#
# In a real bot you'd iterate forever with a sleep between ticks.
# This example does a fixed number of fetches so it terminates.
for tick in range(3):
    try:
        player = client.get_player(allycode=314927874)
        print(f"tick {tick}: {player.name} (level {player.level})")
    except Exception as e:  # noqa: BLE001  — illustrative
        # Anything reaching here has already been retried up to
        # max_retries times — it's a real failure, not a hiccup.
        print(f"tick {tick}: failed after retries — {type(e).__name__}: {e}", file=sys.stderr)
    time.sleep(1.0)

print("done")
