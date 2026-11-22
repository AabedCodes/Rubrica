# <Task ID>: <short title>

- **Author:** <role letter> (@github-handle)
- **Date finished:** YYYY-MM-DD
- **PR / commits:** #<n>, <short SHAs>
- **Threats / controls:** T-nn, Cnn (or "none")
- **Feeds report sections:** §n, §n
- **AI assistance:** none, or <assistant and model>: <which parts>

## What was done

Two to five bullets: what exists now that didn't before.

## How

The approach in a few sentences: main files, how the parts fit, anything non-obvious a reviewer or a teammate's assistant needs to know to build on it.

## Decisions

| Decision | Alternatives considered | Why |
|---|---|---|
| e.g. 5 failed logins per 15 min per account | 10 per hour; exponential backoff | plan's starting value; easy to test in T-28 |

## Deviations from the plan or `01-interfaces.md`

What differs and why, and whether `01-interfaces.md` was updated in this PR. Write "none" if nothing differs.

## Evidence

Tests added and what they prove, CI run links, command output, screenshots. Anything the report §3 verification evidence or the demo can reuse.

## Open items

What's left, what's blocked and on whom, and known weaknesses (these feed §8 residual risk).
