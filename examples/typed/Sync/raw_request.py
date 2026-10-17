# coding=utf-8
"""
raw_request.py — v3-only escape hatch

Sometimes the typed surface doesn't cover an endpoint (new comlink
endpoint, internal-only call, a request shape we haven't typed yet).
``client.raw_request(method, path, payload=None)`` is the escape
hatch — direct HTTP via the underlying httpx client, with the same
the `retry` policy (if set) + auth handling as the typed methods.

Always returns a dict (typed decoding is opt-in per endpoint;
``raw_request`` bypasses that machinery).

Available on both the typed and dict clients with identical
signature. This example uses the typed import for consistency with
``examples/typed/Sync/``.
"""

from swgoh_comlink.typed import SwgohComlink

client = SwgohComlink(url="http://localhost:3200")

# ── 1. GET via raw_request ──────────────────────────────────────────────────
# Equivalent to client.get_enums() but expressed manually:
enums = client.raw_request("GET", "/enums")
print(f"/enums top-level keys: {list(enums.keys())[:5]}...")

# ── 2. POST with a payload ──────────────────────────────────────────────────
# Equivalent to client.get_player(allycode=314927874):
player_dict = client.raw_request(
    "POST",
    "/player",
    payload={"payload": {"allyCode": "314927874"}, "enums": False},
)
print(f"\n/player returned dict with {len(player_dict.get('rosterUnit', []))} units")

# ── 3. When to NOT use raw_request ──────────────────────────────────────────
#
# - Anything covered by a typed-client method: use the typed method.
#   You get attribute access, typed sub-Structs, IDE autocomplete,
#   and decoder caching (msgspec decoders are cached per process).
# - When you'd otherwise re-implement chunking, streaming, or auth
#   yourself — those are baked into the typed methods.
#
# raw_request is for the cases the typed surface genuinely doesn't
# cover. If you find yourself reaching for it often, open an issue
# with the `v3` + `enhancement` labels so we can add a proper typed
# wrapper.
