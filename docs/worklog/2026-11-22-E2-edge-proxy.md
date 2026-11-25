# E2: Edge proxy (egress gap on Docker Desktop)

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-22
- **PR / commits:** #8 (4c4fcd9)
- **Threats / controls:** T-08, T-19 · C06, C12
- **Feeds report sections:** §4.4 (remediation log rows 1 and 2), §4.5, §2
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- New `edge` service: the only container with published ports. It runs the same pinned squid image in accelerator mode and forwards `127.0.0.1:8080` → `web:8000` and `127.0.0.1:8025` → `mailpit:8025`, nothing else. It holds no secrets.
- `web` and Mailpit are now on the `internal` network only.
- `egress_smoke.sh`:
  - Mailpit egress is checked over plain HTTP;
  - new check: `edge` refuses forward proxying;
  - `edge`'s own egress is FAIL on Linux and WARN on Docker Desktop.
- `01-interfaces.md` §2 is updated.

## How

Docker can't publish ports from a container that is only on `internal: true` networks. PR #1 put `web` on a bridge with `enable_ip_masquerade=false`. That blocks outbound traffic on Linux, but **Docker Desktop ignores the option**, which we found when `make up` first ran on E's Windows machine. A reverse proxy at the edge means only a container with no secrets and a fixed forwarding config sits on a routable network.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| squid in accelerator mode, reusing the pinned image | nginx or caddy | no new image to admit, scan and pin |
| `never_direct allow all` plus per-port `cache_peer_access` | default accelerator config | edge can never be used as an open proxy; tested |
| Edge egress on Docker Desktop is a WARN, not a FAIL | fail locally | it can't be fixed there without a VM-level firewall; edge holds nothing worth stealing; Linux CI still fails hard |
| Requests reach `web` with `Host: web` | pass the client host through | fixed and predictable; FastAPI host checks must allow `web` (noted in the PR) |

## Deviations from the plan or `01-interfaces.md`

§2 said `web` is the only service with a published port. Now `edge` is, and §2 was edited in the same PR (E owns §2).

## Evidence

- Local, Docker Desktop 29.9.3: 14/14 services healthy; every check `ok`, plus 1 expected WARN.
- An absolute URL sent to edge returns `web`'s 404, not example.com.
- CI on PR #8: `compose-smoke` green, with `edge direct example.com:80 (blocked)` on Linux.

## Open items

- Residual risk for §8: on developer laptops, `edge` has a route out.
- The Mailpit UI's live-update websocket may not pass through squid; refreshing works.
