# Python ≥3.11 floor for v3.0

**Status:** accepted

v3.0 sets `requires-python = ">=3.11"`, up from v2.x's `>=3.10`.

## Why

3.11 adds language and stdlib features used throughout the v3 design: `typing.Self` for the `_BaseClient.with_options(...) -> Self` shape, `tomllib` for pyproject reads without a third-party dep, `Exception.add_note` for richer error messages, and a ~10–15% interpreter startup improvement that compounds with the Phase 5 lazy-import work to deliver the headline cold-import number.

Dropping 3.10-only users is acceptable for a major version, especially given that `uv` and `pyenv` make multi-version installs trivial for the bot-operator audience that consumes this library.

## Consequences

- `_base_client.py` can use `Self` from `typing` directly; no `typing_extensions` dependency.
- Ruff and mypy targets move to `py311`.
- The Phase 5 cold-import baseline benefits from CPython 3.11's startup work in addition to the SDK's own lazy-loading changes.
- Users on RHEL 9 or Ubuntu 22.04's system Python (3.10 and 3.9 respectively) must install 3.11+ via `uv`, `pyenv`, or `deadsnakes`.
