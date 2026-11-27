# §6 Runtime monitoring and incident response (draft)

Owner: E; C writes 6.3 (how agents stop). The brief asks for: what is logged (every tool call, at minimum), what triggers an alert, how the agent is stopped, and a one-page incident runbook. Status as of 22 Nov 2026: the design is fixed in `01-interfaces.md` §8 and in `docs/plan/E-platform-devsecops-engineer.md` E10/E11; the code lands in E6, E10 and E11.

## 6.1 What is logged

One `audit_log` row (D6) for every MCP tool call, every model call and every human decision (approve release, decide appeal, accept key, pause, kill switch). It is written by `backend/common/audit.py` **[E6]**. Columns are in `01-interfaces.md` §8.

- **Free text is redacted.** Any string argument longer than 64 characters is replaced by `{len, sha256}`. That makes the log safe to show and keeps injected text from flowing back out through it.
- **Append-only.** Every database role has `INSERT` only, and a trigger raises on `UPDATE` or `DELETE` (D1).
- **Tamper-evident.** `hash = SHA-256(prev_hash ‖ canonical JSON)`. `scripts/verify_audit_chain.py` **[E11]** reports the first broken row; it runs nightly and in the T-32 test.
- `orchestrator_transcripts` keeps the planner's full context at every step. By design it contains no student text, which the T-04 test checks for the canary.

TODO: a sample of real rows from the demo run (steps 4 to 6).

## 6.2 Alerts

A `monitor` job runs every minute over new audit rows and writes to `alerts`. It also emails the ops address in Mailpit and shows a banner on the instructor's audit screen. **[E11]** Thresholds are starting values; record the final ones here.

| Rule | Fires when | Threat |
|---|---|---|
| Denial spike | one agent gets more than N `E_SCOPE`, `E_AUTH` or `E_INVALID_ARGS` in 5 minutes | T-02, T-05 |
| Answer-key overlap | any `answer_key_overlap` row | C23 |
| Validator rejections | more than N% of a run's attempts rejected | T-04 |
| Full-marks rate | more than N% of a run flagged `full_marks` | T-04, T-09 |
| Fetcher blocked | any `non_public_address` block | T-08 |
| Budget | 80% and 100% of a course's daily budget | T-25 |
| Tool-list mismatch | an agent refused to start on the MCP hash check | T-18 |
| Chain broken | `verify_audit_chain.py` fails | log tampering |
| Pause or kill switch | any change | operator awareness |

## 6.3 Stopping an agent

C writes this part. It covers what happens step by step when the course pause or the global kill switch flips during a grading run:
- tokens are revoked (E5);
- the adapter and MCP server refuse the next call with `E_PAUSED`;
- the harness sends the remaining submissions to the manual queue;
- the audit rows written along the way.

Evidence: the C30 test (pause during a running job). **[E10, C]**

## 6.4 Infrastructure containment already in place

Even with no alert firing, a misbehaving agent is boxed in by the deployment (see §4.5):
- agents can reach only the provider host, through `llm-proxy`;
- the fetcher can't reach internal ranges;
- the parser has no network and no secrets;
- every service has its own database role and secrets.

`scripts/egress_smoke.sh` proves this on every CI run.

## 6.5 Runbook

[`docs/runbook.md`](../runbook.md), one page: detect, triage, contain, recover, communicate, after the incident. TODO: a timed tabletop run of it once E10 and E11 land, with the timings recorded here.
