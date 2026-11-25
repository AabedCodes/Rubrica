# D8 Citation URL preflight

- **Author** D (@mahashakshuki)
- **Date finished** 2026-11-26
- **PR / commits** [PR #12](https://github.com/omaaryouussef/Rubrica/pull/12), `e2e305d`
- **Threats / controls** C06, T-08
- **Feeds report sections** §2, §3, §8, §9
- **AI assistance** Codex implemented the code, tests, and documentation.

## What was done

- Added defensive validation for citation URLs and resolved addresses.

## How

The preflight checks scheme, credentials, and port, then validates all DNS results and returns the checked addresses to the future transport.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Reject mixed public and private DNS answers | Accept the public subset | The preflight rejects the entire answer if any record is outside the public-address policy. |

## Deviations from the plan or `01-interfaces.md`

This entry covers the preflight portion of D8.

## Evidence

Unit tests cover mixed DNS results and unsupported URL components. The [CI run](https://github.com/omaaryouussef/Rubrica/actions/runs/45714425437) passed.

## Open items

Proxy transport, per-hop redirect validation, snapshot writes, and hosted fixtures remain open.
