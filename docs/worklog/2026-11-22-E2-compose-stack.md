# E2: Compose stack, networks, proxies, hardening

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-22
- **PR / commits:** #1 (cf9b9d1, 83c3ad4)
- **Threats / controls:** T-08, T-15, T-19 · C06, C12, C14, C16
- **Feeds report sections:** §2 (control rows C06, C12, C14), §4.5 blast radius, §6.4
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- `deploy/docker-compose.yml` with all 13 services from `01-interfaces.md` §2.
- One image for every Python service (`deploy/backend.Dockerfile`, targets `runtime` and `web`), with a frontend build stage that tolerates a missing `package.json` until A adds it.
- Two squid egress proxies: `llm-proxy` (CONNECT to the provider host only; the allow-list is a `.invalid` placeholder, so it denies everything) and `web-proxy` (ports 80 and 443; private, loopback, link-local, CGNAT, multicast and documentation ranges denied after DNS resolution).
- `scripts/make_secrets.py` creates 15 Docker secrets with random values. `llm_api_key` is left empty for the real key.
- `backend/common/placeholder.py` and `healthcheck.py`, so every service is healthy before its owner writes it.
- `scripts/egress_smoke.sh`, about 35 checks run after `make up`.

## How

`internal`, `llm-egress` and `web-egress` are `internal: true` networks, so a container on them alone has no route out. Agents reach the internet only through `llm-proxy`, the fetcher only through `web-proxy`, and the parser has `network_mode: none`. Every container:
- runs as non-root (10001 for ours, the image's own user for the others);
- has `read_only: true` with a `tmpfs` for `/tmp`;
- has `cap_drop: [ALL]` and `no-new-privileges`;
- uses `init: true`;
- has a healthcheck;
- uses an image pinned by digest.

Each service gets only its own secrets (see the §4.5 table).

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| squid for both proxies (`ubuntu/squid` 6.10, pinned) | tinyproxy, an nginx stream proxy | squid's `dst` ACLs deny private ranges after DNS resolution, which defeats name tricks like `db` or `localtest.me` |
| One backend image, different `command:` per service | one image per service | one dependency set to scan and pin; least privilege comes from secrets, networks and DB roles, not from image contents |
| postgres starts as uid 999 directly | the image's root entrypoint plus gosu | works with `cap_drop: ALL`; the PG18 data path `/var/lib/postgresql` is a named volume |
| Secret files are mode 0644 inside a 0700 `secrets/` directory | 0600 files | Compose bind-mounts the files with host permissions, and containers run as other UIDs; the directory keeps other host users out |
| Fetcher gets `db_fetch_password` and the grading agent's `X-Service-Auth` secret | no credentials at all (§2 table) | D8 gives it the `rubrica_fetch` role; D decides the final form |
| Parser healthcheck is a heartbeat file | an HTTP healthcheck | it has no network at all |
| Smoke test runs in CI on the GitHub runner | only locally | there was no Docker on E's machine at first; CI gives every PR a real `make up` |

## Deviations from the plan or `01-interfaces.md`

- The first CI run found `web` could reach the internet: it was on the NATed `public` network so its port could be published. Fixed in 83c3ad4 by moving it to a bridge with IP masquerading off. That fix turned out not to hold on Docker Desktop; see `2026-11-22-E2-edge-proxy.md`.
- The fetcher's credentials differ from the §2 table (above). D decides.

## Evidence

CI `compose-smoke` on PR #1, second run: 13/13 services healthy, and every egress, isolation and non-root check passes:
- agents can't reach example.com directly or through `llm-proxy`;
- the fetcher reaches example.com only through `web-proxy`, and `db:5432`, `169.254.169.254` and `127.0.0.1` are denied;
- the parser can't open sockets and has no secrets.

These checks are the network half of the T-15 verification test.

## Open items

- Each owner replaces their service's placeholder `command:` with the real entry point.
- D adds role creation to the DB init (the passwords are already mounted in `db`).
- `llm-allowlist.txt` gets the provider host when keys arrive.
