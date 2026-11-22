# §4 Supply-chain remediation (draft)

Owner: E; D contributes the models and datasets parts. Status as of 22 Nov 2026: structure, controls already in place and the blast-radius table. Scan results, the remediation summary and the drill note are filled in by E8, E12 and E16. `TODO` marks every gap.

## 4.1 What we depend on and how it is pinned

| Component class | How it's pinned | Gate | Status |
|---|---|---|---|
| Python packages | `backend/uv.lock` (hashes), `uv sync --frozen` | CI `lint`/`test` fail on a stale lock | done |
| npm packages | `frontend/package-lock.json`, `npm ci --ignore-scripts` | `pins` job requires the lockfile once `package.json` exists | waits on A's frontend |
| Container images | `image: name@sha256:…` and `FROM …@sha256:…` | `scripts/check_pins.py` (CI `pins`) | done (python, node, uv, pgvector, squid, mailpit) |
| CI actions | full commit SHA plus version comment | `check_pins.py` | done |
| Embedding model `BAAI/bge-small-en-v1.5` | exact revision plus SHA-256 in `aibom/models.lock`, `.safetensors` only | `check_models.py` + ModelScan (E8) | TODO (D picks the revision) |
| Hosted model | provider snapshot ID in the AI-BOM | review | TODO (no keys yet) |
| Coding assistants | `CLAUDE.md`, `.claude/settings.json`, review gate | see §5 | done |

## 4.2 Package admission (C14, T-16)

`scripts/admission_check.py` checks three things before any package is added:
- **Exists:** catches hallucinated names.
- **Not a lookalike:** edit distance ≤ 2 from a known package (`scripts/known_packages.txt`) needs review.
- **Credible history:** ≥ 90 days old, ≥ 5 releases, linked source repository. A pinned version younger than 14 days needs review.

Evidence so far:
- `pytest 9.2.0`, `ruff 0.17.4` and their 5 transitive packages: PASS (output in PR #1).
- Misspelled name `reqeusts`: FAIL, "does not exist … did you mean: requests?" (we constructed this by misspelling a real package, which E7 allows).
- `ruff 0.17.6`, 3 days old at the time: we chose `0.17.4` because of the 14-day rule.
- TODO: `pyotp` admitted in E4's PR; a real assistant-suggested nonexistent package, if one comes up.

## 4.3 SBOM and AI-BOM

TODO (E8): CycloneDX for the Python environment, the npm lockfile and each image, merged with `aibom/aibom.cdx.json`. It is generated in CI on every build and uploaded as an artifact; `make sbom` produces the same file locally. `scripts/am_i_affected.py` searches it.

## 4.4 Scan results and remediation log summary

TODO (E12): OSV-Scanner, pip-audit, npm audit, Trivy and gitleaks on the first full build, with counts by severity and decision. Show one real fix with before-and-after scans.

Findings already found by our own pipeline (these go into `docs/remediation-log.md`):

| Finding | Source | Severity | Decision | Change | Verification |
|---|---|---|---|---|---|
| `web` container could reach the internet (it was on the NATed `public` network to publish its port) | CI `compose-smoke` | High (T-19 blast radius, exfiltration route from the service holding session and TOTP secrets) | isolate | PR #1, commit 83c3ad4 (no-NAT ingress network) | `compose-smoke` green |
| The same fix doesn't hold on Docker Desktop: `web` and Mailpit still had egress | local `make up` plus `egress_smoke.sh` | High | isolate | edge reverse proxy owns the published ports; `web` and Mailpit are internal-only | `egress_smoke.sh` locally and in CI |

## 4.5 Blast radius per service

Taken from `deploy/docker-compose.yml`. Use this table to answer "who is affected and what could they reach" in the drill. Database rights come from `01-interfaces.md` §3.2.

| Service | Networks | Route out | Secrets mounted | DB role |
|---|---|---|---|---|
| `edge` | ingress, internal | none on Linux; yes on Docker Desktop | none | none |
| `web` | internal | none | db_web, service_auth_web, token_pepper, session_secret, totp_encryption_key | rubrica_web |
| `grading-agent` | internal, llm-egress | provider host via llm-proxy only | db_grading, service_auth_web, service_auth_grading_agent, llm_api_key | rubrica_grading |
| `chat-agent` | internal, llm-egress | provider host via llm-proxy only | service_auth_web, llm_api_key | none |
| `instructor-agent` | internal, llm-egress | provider host via llm-proxy only | service_auth_web, llm_api_key | none |
| `fetcher` | internal, web-egress | public web via web-proxy (non-public ranges denied) | db_fetch, service_auth_grading_agent | rubrica_fetch |
| `ingestion` | internal | none | db_ingest | rubrica_ingest |
| `parser` | none (`network_mode: none`) | none | none | none |
| `mcp-server` | internal | none | db_mcp, token_pepper | rubrica_mcp |
| `release` | internal | none | db_release, service_auth_web | rubrica_release |
| `db` | internal | none | all db_* passwords (for role setup) | owner |
| `mailpit` | internal | none | none | none |
| `llm-proxy` | llm-egress, public | allow-list: provider host only | none | none |
| `web-proxy` | web-egress, public | public internet, non-public ranges denied | none | none |

All containers run as non-root with a read-only root filesystem, `cap_drop: [ALL]` and `no-new-privileges`. `egress_smoke.sh` checks each of these properties on every CI run.

## 4.6 Advisory drill note

TODO (E16): practice run by Wed 2 Dec, using the two-page format with exposure, blast radius, remediation, verification and communication, plus the time it took to answer question 1.
