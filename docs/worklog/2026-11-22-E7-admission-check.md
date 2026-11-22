# E7: Package admission check

- **Author:** E (@AabedCodes)
- **Date finished:** 2026-11-22
- **PR / commits:** #1 (3f2720b)
- **Threats / controls:** T-16 · C14
- **Feeds report sections:** §4.2, §3 (T-16 evidence)
- **AI assistance:** Claude Code (Claude Opus 5.5) wrote all files, under E's direction

## What was done

- `scripts/admission_check.py <pypi|npm> <name> [version]` prints PASS, REVIEW or FAIL with reasons, with exit codes 0, 2 and 1.
- `scripts/known_packages.txt`: our stack plus the most-downloaded packages in each ecosystem, used for lookalike detection.
- 13 offline unit tests with fixture registry responses, plus 1 opt-in live test.

## How

The script runs three checks:
1. **Exists:** the PyPI or npm JSON API is queried; a 404 means FAIL, which catches hallucinated names.
2. **Intended package:** Damerau-Levenshtein distance ≤ 2 from a different known name means REVIEW. PEP 503 name normalisation is applied first, and names of 4 characters or fewer only match at distance 1.
3. **Credible history:** first release ≥ 90 days ago, ≥ 5 releases, and a source repo on GitHub, GitLab, Codeberg, Bitbucket or sr.ht; otherwise REVIEW.

The source-repo URL is trimmed to `host/owner/repo`. The script uses only the standard library and accepts only the two registry URL prefixes.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Thresholds 90 days, 5 releases, repo linked | the plan's starting values | kept as given; record any change here |
| Added: a pinned version younger than 14 days needs REVIEW | no version-age check | most malicious releases of real packages are caught within days; this is why we chose ruff 0.17.4 over 0.17.6 |
| For PyPI, report "authors" | "maintainers" | PyPI's JSON API doesn't expose account maintainers, only free-text author fields; the label says what it really is |
| A registry outage gives REVIEW | FAIL | an outage isn't evidence against the package; the person retries |

## Deviations from the plan or `01-interfaces.md`

Only the version-age rule above, which is stricter than the plan.

## Evidence

Run on 22 Nov:
- `pyotp`: PASS.
- `pytest 9.2.0`, `ruff 0.17.4` and their 5 transitive packages: PASS (output pasted in PR #1).
- `reqeusts`: FAIL, "does not exist … did you mean: requests?". This name was constructed by misspelling a real package, which E7 allows. No assistant has suggested a nonexistent package yet.

## Open items

- E8 `admission` CI job: check that a PR changing a lockfile pastes this output for each new package.
- Keep `known_packages.txt` in sync with the lockfiles.
- If a real AI-suggested nonexistent package comes up, save its FAIL output for §4.
