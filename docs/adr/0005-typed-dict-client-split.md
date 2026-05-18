# Split typed and dict client surfaces across two import paths, supported by manifest-driven codegen

**Status:** accepted (v3.1-research)

`swgoh_comlink` ships **two client surfaces** at two import paths:

- `from swgoh_comlink import SwgohComlink` — **dict-default**. Returns
  raw `dict[str, Any]` shapes. Byte-compatible with v2's wire surface.
- `from swgoh_comlink.typed import SwgohComlink` — **typed-default**.
  Returns `msgspec.Struct` instances (the v3 research format).

Async twins (`SwgohComlinkAsync`) live alongside in each module.

All four client classes (2 sync/async × 2 dict/typed) are
**code-generated** from a single manifest
(`src/swgoh_comlink/_codegen/endpoints.py`) via a Jinja template
(`templates/client.py.jinja`) and generator script
(`generate.py`). A pre-commit hook + CI step enforce
`make generate && git diff --exit-code` to prevent drift.

## Why two surfaces

The original v3 design (Phase 3) made typed Structs the default and
shipped `raw=True` as an opt-out per call. That made v3 a hard break
from v2: every dict access (`player["name"]`) became broken under v3
unless the caller passed `raw=True` everywhere or wrapped with
`compat.to_dict()`.

For a **standalone research repo** (ADR-0001) with one caller, that
cost was acceptable. For **eventual reintegration** with the public v2
repo, it would force every existing v2 user to rewrite their code on
upgrade.

Splitting the surface restores the v2 upgrade path: existing dict-style
code keeps working byte-for-byte; users who want the typed surface
change one import line. The split also gives a cleaner mental model —
each module's docs describe one shape, not both with conditional logic
for a `raw=` kwarg.

## Why codegen

Without codegen, this split would mean **four hand-maintained client
classes** with ~16 endpoint methods each — ~64 method bodies of
near-identical code. Phase 4 explicitly noted that the existing
sync/async duplication (0.98 ratio, ~125 SLOC per client) was
unmanageable without a generation tool, and deferred unasync as the
candidate.

Adding the dict/typed axis on top makes hand-maintenance untenable. The
codegen turns four parallel clients into:

- One manifest (one Python entry per endpoint).
- One Jinja template (parametrized on `is_async`, `is_typed`).
- One generator script.

Adding an endpoint = one manifest entry + regenerate. Diff size in PRs
is large but mechanical (4 generated files plus the 1-line manifest
change); reviewers focus on the manifest entry, not the four method
bodies it implies.

## Rejected alternatives

**Typed-default + `raw=True` everywhere (original v3.0 design).** Forces
v2 users to rewrite on upgrade. Documented as the wrong reintegration
shape; we kept it for v3.0 only because v3.0 was research-only and the
public repo wasn't on the roadmap.

**Inheritance with a class-level `_DEFAULT_RAW` flag.** The dict client
would inherit from the typed client and flip a flag. Return-type
annotations don't narrow on inheritance: both subclasses would advertise
`Player | dict[str, Any]`, defeating the type-checker win that is half
the reason to split.

**Pure metaclass dispatch.** Same class, runtime-swapped return shape
via `__init_subclass__` or `__getattribute__`. mypy-hostile;
debugging-hostile; magic that future readers wouldn't grep for.

**`unasync` for the sync/async axis only.** Standard tool, but it only
addresses one of the two axes. We'd still hand-maintain dict/typed.
Pure manifest-driven Jinja covers both axes from one source — simpler.

**Codegen `_payloads.py` or `_models.py`.** Payload builders carry
validation logic; Structs carry schema specifics. Generating them
would multiply the toolchain for no maintenance win. They stay
hand-maintained; the manifest *references* them by name.

## Consequences

- **For existing v3-research callers (internal):** one-line import
  change (`swgoh_comlink.SwgohComlink` → `swgoh_comlink.typed.SwgohComlink`)
  to keep typed access. Migration guide documents this.
- **For future v2 reintegration:** existing v2 callers keep working
  without code change. Typed access is opt-in via the new import path.
  This becomes the recommended upgrade pattern.
- **For maintainers:** all endpoint changes happen in the manifest; the
  four client files are generated and marked `DO NOT EDIT`. A
  pre-commit hook enforces regeneration when the manifest changes.
- **For Phase 5's lazy-import discipline:** the dict client's imports
  don't pull msgspec Structs at module load — only the typed client
  does. Cold-import time on `import swgoh_comlink` stays in the ~7 ms
  range that Phase 5 measured.
- **Escape hatches (`healthcheck`, `raw_request`, `stream_game_data`,
  `stream_localization`)** stay hand-written in mixins
  (`_escape_hatches_sync.py` / `_escape_hatches_async.py`). Their
  bodies are non-uniform (different return shapes, no decoder dispatch,
  bypass retry, streaming context managers); manifest-ifying them
  would force conditional branches that outweigh the duplication win.
- **`_payloads.py` and `_models.py` stay the source of truth** for
  payload shapes and Struct definitions. They're imported by name from
  the generated files; manifest entries reference them as strings
  (`payload_builder="player_payload"`, `typed_decoder="PLAYER_DECODER"`).
