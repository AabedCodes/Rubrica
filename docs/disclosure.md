# Reporting a security issue in Rubrica

**Status: draft (A10).** Owner: A. Linked from the [system card](system-card.md) §9. Two decisions are still open (marked `TODO`) before this is final.

Rubrica is a student capstone project that runs only on synthetic data. If you find a security issue, please tell us privately so we can fix it before others are affected.

## Where to report

Use the repository's **private vulnerability reporting** ("Report a vulnerability" under the Security tab).

`TODO(repo admin)`: enable private vulnerability reporting on the repository; until then this link doesn't exist.

Please don't open a public issue or pull request for a security problem, and don't email individual team members.

## What to include

- What you found, and where: file, route or screen.
- Steps to reproduce on a local stack (`make up`, then `make seed`).
- What an attacker could do with it.
- Any canary you used to prove it. Harmless markers only, such as a `CANARY-…` string.

## What we commit to

- Acknowledge your report within `TODO(team)` working days. The draft suggests 3.
- Investigate it, and tell you whether we could reproduce it.
- Fix confirmed issues, or explain why we won't.
- Tell you when the fix is merged.
- Credit you in the project report and repository, if you want.

We are five students working during a semester. These are best-effort commitments, not a service-level agreement.

## What we ask in return

- Test only against your own local copy, with synthetic data. Never use real student data.
- Don't test other teams' systems or any hosted service.
- Use harmless canaries, not real attack payloads.
- Give us reasonable time to fix the issue before you discuss it publicly.
