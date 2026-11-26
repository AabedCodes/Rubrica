# D7 Course blog indexing

- **Author** D (@mahashakshuki)
- **Date finished** 2026-11-26
- **PR / commits** Local follow-up
- **Threats / controls** T-06, T-13, T-20, C03, C24
- **Feeds report sections** ?2, ?3, ?9
- **AI assistance** Codex wrote the worker, migrations, tests, and documentation.

## What was done

- Added background indexing for blog posts and comments.
- Added transactional enqueueing on insert and cleanup on delete. The migration queues existing sources.

## How

The worker leases a job, loads source text and author from the database within
the job's course, and stores embeddings in the blog collection with server-set
trust labels. The source rows remain locked while chunks are written.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Read body and author from the stored row | Copy post text into the job payload | Retries use the authorized source and avoid duplicating untrusted text in the queue. |

## Deviations from the plan or `01-interfaces.md`

This entry covers the indexing and cleanup pieces. The shared interface document is unchanged.

## Evidence

PostgreSQL regression coverage checks course scoping, source trust, idempotent
indexing and deletion cleanup. A Compose smoke test confirmed that seeding automatically queued and indexed the T13 comment as untrusted.

## Open items

Authenticated blog routes still need the shared identity and membership code.
