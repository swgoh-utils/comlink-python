# Installing the v3 alpha safely

The v3 alpha ships as the **same package name** (`swgoh_comlink`) as the
stable v2.x release on PyPI, but it is **not on PyPI** — it is only
available as a GitHub Release asset on
[MarTrepodi/comlink-python](https://github.com/MarTrepodi/comlink-python)
(see [ADR-0008](../adr/0008-pre-release-distribution-via-github-releases.md)).
That name-sharing is deliberate (the alpha is the future of the same
package), but it means you should install it in a way that can't
silently interfere with — or be silently replaced by — the public v2.x
release. This guide covers exactly that.

**Rule zero: never install the alpha into a shared or system
environment.** Always use a dedicated virtual environment.

## 1. Isolated install (recommended)

Create a virtual environment used only for the alpha:

```bash
# with uv (recommended)
uv venv .venv-swgoh-v3
source .venv-swgoh-v3/bin/activate    # Windows: .venv-swgoh-v3\Scripts\activate
uv pip install https://github.com/MarTrepodi/comlink-python/releases/download/v3.0.0a1/swgoh_comlink-3.0.0a1-py3-none-any.whl
```

```bash
# stdlib equivalent
python3.11 -m venv .venv-swgoh-v3
source .venv-swgoh-v3/bin/activate
pip install https://github.com/MarTrepodi/comlink-python/releases/download/v3.0.0a1/swgoh_comlink-3.0.0a1-py3-none-any.whl
```

Verify what you got:

```bash
python -c "import swgoh_comlink; print(swgoh_comlink.version)"
# -> 3.0.0a1
```

Your existing v2 environments are untouched — the alpha lives only
inside `.venv-swgoh-v3`, and deleting that directory removes it
completely.

## 2. Guard against silent replacement by PyPI v2.x

Because the alpha is not on PyPI, any later dependency resolution that
re-installs `swgoh_comlink` **from PyPI** can only find v2.x. Pin the
alpha in a constraints file so that scenario fails loudly instead of
silently downgrading you:

```text
# constraints.txt
swgoh_comlink==3.0.0a1
```

```bash
pip install -c constraints.txt <anything-else-you-add-to-this-env>
```

With the pin in place, a resolver that tries to fetch `swgoh_comlink`
from PyPI errors out ("no matching distribution for
swgoh_comlink==3.0.0a1") rather than replacing your alpha with v2.x.

Notes on specific commands:

- `pip install -U swgoh_comlink` will **not** downgrade you — pip sees
  the installed `3.0.0a1` as newer than anything on PyPI and keeps it.
- `pip install --force-reinstall swgoh_comlink` (or uninstall +
  reinstall by name) **will** land you on v2.x, because by-name
  installs resolve against PyPI. Reinstall from the wheel URL instead.

## 3. uv-managed projects

If the consuming project is uv-managed, pin the alpha as a direct-URL
source so the lockfile records exactly this artifact:

```bash
uv add "swgoh_comlink @ https://github.com/MarTrepodi/comlink-python/releases/download/v3.0.0a1/swgoh_comlink-3.0.0a1-py3-none-any.whl"
```

`uv.lock` then holds the URL + hash; `uv sync` reproduces the alpha
exactly and will never "helpfully" resolve `swgoh_comlink` from PyPI.

## 4. Switching back to the public v2.x release

**Preferred: throw away the alpha environment.** Nothing to undo:

```bash
deactivate
rm -rf .venv-swgoh-v3
```

Your v2 environments were never touched.

**In-place rollback** (same environment), if you must:

```bash
pip uninstall -y swgoh_comlink
pip install "swgoh_comlink==2.*"
```

(Remove the `constraints.txt` pin first, and the direct-URL source /
`uv.lock` entry in uv-managed projects.)

!!! warning "Rolling back the package does not roll back your code"
    Code written against the v3 typed surface
    (`from swgoh_comlink.typed import SwgohComlink`, `msgspec.Struct`
    returns, `GameDataCache`, bimorphic `StatCalc`) will not run on
    v2.x. If you adopted v3 APIs, switching back means reverting those
    call sites too — [the migration guide](migration.md) documents the
    v2 ↔ v3 differences. Code that only ever used the dict-default
    `from swgoh_comlink import SwgohComlink` works identically on both.

## Reporting problems

Open issues at
[MarTrepodi/comlink-python/issues](https://github.com/MarTrepodi/comlink-python/issues)
with the `v3` label — see the
[release notes](releases/v3.0.0a1.md) for what to include.
