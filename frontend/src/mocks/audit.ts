/**
 * MOCK(E11) audit writer for the mock world (01-interfaces.md §8).
 * The real log is append-only and hash-chained in the database; here rows are
 * appended in memory so the audit view (A7) has real entries to show.
 */
import type { AuditRow } from "../types/oversight";
import type { MockContext } from "./http";

type NewRow = Partial<Omit<AuditRow, "id" | "ts" | "actor_display">> & Pick<AuditRow, "action">;

export function writeAudit(ctx: MockContext, row: NewRow): void {
  ctx.world.audit.push({
    id: ctx.world.newId(),
    ts: new Date(ctx.now()).toISOString(),
    actor_kind: "user",
    actor_id: ctx.user.id,
    on_behalf_of: null,
    course_id: null,
    args_redacted: {},
    decision: "allowed",
    reason_code: null,
    result_summary: {},
    model_id: null,
    prompt_version: null,
    ...row,
  });
}
