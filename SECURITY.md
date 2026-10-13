# Security Policy

## Supported Versions

Security fixes are released for the latest minor version of the current major release line.
Older releases do not receive patches — please upgrade to the latest version.

| Version | Supported          |
|---------|--------------------|
| 2.x (latest minor) | :white_check_mark: |
| 2.x (older minors) | :x: |
| 1.x     | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests,
or in the Discord server.**

Report them privately through GitHub's
[private vulnerability reporting](https://github.com/swgoh-utils/comlink-python/security/advisories/new)
(**Security** tab → **Report a vulnerability**). This keeps the report confidential between you and the
maintainers until a fix is available.

Please include as much of the following as you can:

- The affected version(s) of `swgoh_comlink` and Python
- The affected component (sync/async client, HMAC signing, `StatCalc`, helpers, `swgoh-migrate`, ...)
- A description of the issue and its impact
- Step-by-step instructions or a minimal proof of concept to reproduce it
- Any suggested mitigation or fix

**Never include real credentials** (comlink `access_key` / `secret_key`) in a report. Use placeholder values.

## What to Expect

This project is maintained by volunteers, so timelines are best-effort:

- **Acknowledgement** of your report within 7 days
- **Initial assessment** (confirmed, needs more info, or not a vulnerability) within 14 days
- **Fix and disclosure** coordinated with you. Once a patched release is on PyPI, a GitHub Security
  Advisory is published, crediting you unless you prefer to stay anonymous

## Scope

**In scope** — vulnerabilities in this library, for example:

- Leaking `access_key` / `secret_key` (or other sensitive values) through logs, `repr()`, exceptions, or
  request data
- Flaws in HMAC request signing
- TLS certificate verification being bypassed when `verify_ssl=True`
- Path traversal or unsafe file handling in helper file I/O utilities or the `swgoh-migrate` tool
- Unsafe deserialization or processing of data returned by a comlink service

**Out of scope** — please report these elsewhere:

- Vulnerabilities in the [swgoh-comlink](https://github.com/swgoh-utils/swgoh-comlink) service itself — report
  them to that project
- Vulnerabilities in third-party dependencies (e.g. `httpx`) that are not caused by how this library uses them —
  report them upstream
- Issues that need a misconfigured or already-compromised environment (e.g. a malicious comlink URL you chose to
  trust with `verify_ssl=False`)
- Anything concerning the game itself or its terms of service
