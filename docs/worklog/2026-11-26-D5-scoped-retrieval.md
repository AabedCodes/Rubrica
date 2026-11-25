# D5 Course-scoped retrieval

- **Author** D (@mahashakshuki)
- **Date finished** 2026-11-26
- **PR / commits** [PR #12](https://github.com/omaaryouussef/Rubrica/pull/12), `e2e305d`
- **Threats / controls** C03, C24, C35
- **Feeds report sections** §2, §3, §8, §9
- **AI assistance** Codex implemented the code, tests, and documentation.

## What was done

- Added course-scoped cosine retrieval for the chat and grading paths.

## How

Retrieval uses the caller’s PostgreSQL transaction. Chat includes material and blog chunks. Grading queries published material and its source metadata.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| Separate chat and grading queries | One shared query with application-side filtering | The grading query never touches the blog collection. |

## Deviations from the plan or `01-interfaces.md`

The retrieval functions take an explicit encoder callable. The shared interfaces document was left as written.

## Evidence

PostgreSQL regression tests cover cross-course exclusion, published material, blog separation, and result limits.

## Open items

Wire the functions into the MCP tools and the grading context assembler.
