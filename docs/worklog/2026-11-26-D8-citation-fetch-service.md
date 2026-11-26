# D8 citation fetch service

- **Author** D (@mahashakshuki)
- **Date finished** 2026-11-26
- **PR / commits** Local follow-up to PR #12
- **Threats / controls** T-07, T-08, T-21, C06, C31
- **Feeds report sections** §2, §3, §8, §9
- **AI assistance** Codex implemented the transport, service, tests, and documentation.

## What was done

- Connected the internal endpoint to address validation, HTTPS proxy transport, and scoped snapshot persistence.
- Added redirect rechecks, content-type and body limits, and redacted event logging.
- Added a DNS-only helper on the proxy network for Docker's internal-network isolation.

## How

The caller sends its grading service credential and the verified run and course
IDs. The fetcher checks submission scope before outbound work. It verifies TLS
against the original hostname over a tunnel to the checked numeric address and
stores the response or failure under the same database context.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Use a DNS helper on the proxy network | Give the fetcher direct internet access | The fetcher retains its existing network isolation. |
| Require the proxy's HTTPS CONNECT path | Send plain HTTP through a hostname request | A numeric tunnel keeps the origin connection pinned to a checked address. |

## Deviations from the plan or `01-interfaces.md`

The existing proxy permits CONNECT only on port 443. Plain HTTP is blocked
pending an agreed address-pinned transport. The service logs fixed codes
pending the shared hash-chain writer.

## Evidence

Unit tests cover numeric CONNECT, TLS origin verification, redirect checks,
plain HTTP rejection, and the response size limit. The Docker smoke test fetched a public HTTPS page and verified that authenticated requests produced separate fetched and blocked snapshots. Cross-course and unauthenticated requests received HTTP 403.

## Open items

Plain HTTP transport, hash-chain integration, hosted citation fixtures, and
the grading-agent caller.
