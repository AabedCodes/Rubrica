# Incident runbook: a misbehaving agent

Owner: E (C co-owns agent stopping). One page, written to be followed under pressure. Items marked **[E10]**, **[E11]** etc. depend on tooling that task delivers. Until it lands, use the fallback given.

**Roles during an incident.** *Incident lead*: E, or whoever is on call. *Agent expert*: C. *Communications*: A. *Scribe*: anyone. Write a timestamped note of every action in the incident issue.

## 1. Detect

| Signal | Where it shows up | Likely meaning |
|---|---|---|
| Denial spike (`E_SCOPE`, `E_AUTH`, `E_INVALID_ARGS`) from one agent | `alerts` table, ops email in Mailpit, instructor audit banner **[E11]** | a fooled agent probing its limits (T-02, T-05) |
| Full-marks rate or validator rejections above threshold in a run | same **[E11]** | injected or poisoned submissions; bad prompt version (T-04) |
| `answer_key_overlap` row | same **[E11]** | answer-key text leaking into feedback (C23) |
| Fetcher `non_public_address` block | same **[E11]** | SSRF attempt (T-08) |
| Budget at 80% or 100% | same **[E9]** | flood or runaway loop (T-25) |
| MCP tool-list hash mismatch | agent refuses to start **[C]** | tampered tool descriptions (T-18) |
| `verify_audit_chain.py` fails | nightly job **[E11]** | log tampering |
| A person reports it | team chat, instructor, student, or a disclosure report | anything |

## 2. Triage (about 10 minutes)

Decide which **agent**, which **course** and which **run** are involved, and whether data was changed or only attempted.

- One agent: `GET /api/courses/{id}/audit?actor_id=grading-agent` **[audit route]**. Fallback: `make up`, then `docker compose -f deploy/docker-compose.yml exec db psql -U rubrica_owner -d rubrica -c "SELECT ts, action, decision, reason_code, result_summary FROM audit_log WHERE actor_id = 'grading-agent' ORDER BY id DESC LIMIT 100"`
- One run: filter `on_behalf_of = '<run_id>'`. Read `orchestrator_transcripts` for that `run_id` to see what the planner saw.
- What changed: look for `decision = 'allowed'` rows with a side effect (`store_proposed_grade`, `open_appeal`, `draft_*`, `propose_grade_change`). Released grades need a human approval row (`approve_release`), so check whether one exists.
- Severity: **SEV1** means a grade was released, data from another course or student left its boundary, or a credential leaked. **SEV2** means a side effect was written but not released. **SEV3** means attempts only, all denied.

## 3. Contain (SEV1 or SEV2: do this before investigating further)

1. **One course:** the instructor presses *Pause agents*, or calls `POST /api/courses/{id}/pause` (re-auth) **[E10]**. Agents' tokens for that course are revoked. Submissions keep working. In-flight runs stop at their next model or tool call, and the remaining submissions go to the manual queue.
2. **Everything:** `python scripts/kill_switch.py on --reason "<why>"` **[E10]**. Every agent token is revoked, and the model adapter and MCP server refuse all calls. Fallback until E10 lands: `docker compose -f deploy/docker-compose.yml stop grading-agent chat-agent instructor-agent mcp-server`
3. **Revoke tokens** for an affected user or run if the pause didn't cover them (`identity.tokens.revoke_for(...)`) **[E5]**.
4. **Rotate** any key the agent or attacker could have seen:
   - delete the file in `secrets/`, run `make secrets`, then `make up`;
   - for the provider API key, also revoke it in the provider console;
   - for a GitHub credential, revoke it in GitHub settings.
5. **Hold releases:** nothing is released without instructor approval, so tell instructors not to approve anything from the affected run.

## 4. Recover

- Reject affected proposed grades. Move their submissions to the manual queue, or re-run grading after the fix.
- Run `python scripts/verify_audit_chain.py` **[E11]** and save the output. A broken chain means you treat the log as evidence of tampering.
- Fix, merge through a reviewed PR with green CI, redeploy, then resume: `POST /api/courses/{id}/resume` or `kill_switch.py off`.
- Watch the alerts for one full grading run before declaring it closed.

## 5. Communicate

Instructors hear from A within 1 hour of a SEV1 or SEV2. Students are told only if their grade or data was affected.

> **Subject:** Rubrica: grading agents paused for course `<code>`
> We paused automated grading for `<course>` at `<time>` after detecting `<one-line, non-technical summary>`. No grades are released without your approval; `<N>` proposed grades from run `<id>` have been withdrawn and will be re-graded or graded manually. Submissions are unaffected. Next update by `<time>`. Contact: `<name>`.

## 6. After the incident

- Add a `docs/remediation-log.md` entry: finding, source, severity, decision, change (commit or PR), verification.
- Tell B the same day. B adds the threat or adjusts its rating, and adds a verification test with a `CANARY-T<nn>-<hex>` input that reproduces it.
- Hold a 15-minute review: what was detected, how long each step took, and what to automate next.
