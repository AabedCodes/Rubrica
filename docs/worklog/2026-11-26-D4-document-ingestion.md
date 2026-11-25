# D4 Isolated document ingestion

- **Author** D (@mahashakshuki)
- **Date finished** 2026-11-26
- **PR / commits** [PR #12](https://github.com/omaaryouussef/Rubrica/pull/12), `e2e305d`
- **Threats / controls** C04, C14, C15, T-15, T-29, T-36
- **Feeds report sections** §2, §3, §8, §9
- **AI assistance** Codex implemented the code, tests, and documentation.

## What was done

- Added the Compose ingestion worker for material and submission jobs and pinned the local embedding files.

## How

The worker leases jobs, stages uploads for the isolated parser, validates the stored upload hash, and writes scoped results. Material chunks keep the stored publication state. Submission text stays in the submissions table.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Stable chunk IDs and offline, hash-verified BGE files | Random IDs and runtime model downloads | Retries avoid duplicates and runtime inference needs no network. |

## Deviations from the plan or `01-interfaces.md`

Chunks start at 300 words with 30 words of overlap. The encoder truncates at 512 model tokens.

## Evidence

The Docker smoke test parsed a queued upload and stored one 384-dimensional vector. Regression tests cover job leasing, retries, and parsed-submission scope.

## Open items

The authenticated upload route still needs to enqueue jobs.
