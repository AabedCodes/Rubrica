# Remediation log

Owner: E (D for models and datasets). Columns follow Appendix D of the brief. Record every finding: from scanners, from the M1 Part A assessment, from our own tests, from review, and from incidents. Accepted findings also go in `security/accepted-findings.yaml` with a justification and an expiry date.

| # | Finding | Source | Severity | Decision | Change | Verification |
|---|---|---|---|---|---|---|
| 1 | `web` container had an outbound internet route: it sat on the NATed `public` network so its port could be published | CI `compose-smoke` (`egress_smoke.sh`), 22 Nov | High | isolate | PR #1, commit 83c3ad4: moved to a bridge with IP masquerading off | `compose-smoke` green on the Linux runner |
| 2 | Fix #1 does not hold on Docker Desktop, which ignores `enable_ip_masquerade=false`; `web` and Mailpit reachable to the internet on developer laptops | local `make up` + `egress_smoke.sh`, 22 Nov | High | isolate | branch `e/edge-proxy-and-e14`: new `edge` reverse proxy (pinned squid, no secrets) owns the published ports; `web` and Mailpit internal-only | `egress_smoke.sh` locally (Docker Desktop 29.9.3) and in CI; `edge` egress is a known residual on Docker Desktop only (WARN) |
| 3 | Assistant session started outside the repository did not load `.claude/settings.json`, so the `git push` deny rule did not apply | review of the 22 Nov session | Medium | policy change | `docs/ai-assisted-development.md` §3: always start assistants from the repo root; per-member deny test | TODO: each member's deny test recorded in SC-51 table |
| | TODO (E12): first full scan of all images and lockfiles | | | | | |
