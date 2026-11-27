import { useCallback, useMemo, useState } from "react";
import { useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { oversightRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";
import type { AuditRow } from "../../types/oversight";

interface ScoreChange {
  criterion_id: string;
  before: number;
  after: number;
}

/** Before and after values recorded with an approval or appeal decision (A5, A7). */
export function scoreChangesOf(row: AuditRow): ScoreChange[] {
  const raw = row.args_redacted.score_changes;
  if (!Array.isArray(raw)) return [];
  return raw.filter(
    (c): c is ScoreChange =>
      typeof c === "object" && c !== null && typeof (c as ScoreChange).before === "number" && typeof (c as ScoreChange).after === "number",
  );
}

/** A compact, text-only rendering of IDs and counts. Never renders HTML. */
function summary(obj: Record<string, unknown>): string {
  return Object.entries(obj)
    .filter(([k]) => k !== "score_changes")
    .map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(", ");
}

const shortId = (id: string | null) => (id ? id.slice(-6) : "—");

/**
 * Audit view (C37, R9; demo step 7). A filterable table of the course's audit
 * rows, the chain status from E's verifier, and E11's alerts as a banner.
 */
export function AuditPage() {
  const { courseId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(() => oversightRoutes(api).audit(courseId), [api, courseId]);
  const { state } = useLoad(loader);
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const [decision, setDecision] = useState("");
  const [onBehalf, setOnBehalf] = useState("");

  const rows = useMemo(() => (state.status === "ok" ? state.data.rows : []), [state]);
  const filtered = useMemo(
    () =>
      rows.filter(
        (r) =>
          (!actor || r.actor_display === actor) &&
          (!action || r.action === action) &&
          (!decision || r.decision === decision) &&
          (!onBehalf || (r.on_behalf_of ?? "").includes(onBehalf.trim())),
      ),
    [rows, actor, action, decision, onBehalf],
  );

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const { chain, alerts } = state.data;
  const actors = [...new Set(rows.map((r) => r.actor_display))].sort();
  const actions = [...new Set(rows.map((r) => r.action))].sort();

  return (
    <section>
      <h1>Audit log</h1>
      {alerts.map((a) => (
        <div key={a.id} className={`banner banner-alert severity-${a.severity}`} role="alert">
          <strong>Alert: {a.rule.replaceAll("_", " ")}</strong> ({a.severity}), {formatDate(a.created_at)}. {summary(a.details)}
        </div>
      ))}
      <p className={chain.status === "intact" ? "chain-ok" : "error"} role="status">
        Hash chain {chain.status === "intact" ? "intact" : "BROKEN"}: {chain.rows_checked} rows checked
        {chain.first_broken_row && `; first broken row ${chain.first_broken_row}`}.
      </p>

      <form className="filters" aria-label="Filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Actor
          <select value={actor} onChange={(e) => setActor(e.target.value)}>
            <option value="">All</option>
            {actors.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </label>
        <label>
          Action
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">All</option>
            {actions.map((a) => (
              <option key={a}>{a}</option>
            ))}
          </select>
        </label>
        <label>
          Decision
          <select value={decision} onChange={(e) => setDecision(e.target.value)}>
            <option value="">All</option>
            <option value="allowed">allowed</option>
            <option value="denied">denied</option>
          </select>
        </label>
        <label>
          On behalf of (run or user ID)
          <input value={onBehalf} onChange={(e) => setOnBehalf(e.target.value)} placeholder="paste an ID" />
        </label>
      </form>
      <p className="muted">
        Showing {filtered.length} of {rows.length} rows, newest first.
      </p>

      <table className="table compact" aria-label="Audit rows">
        <thead>
          <tr>
            <th>Time</th>
            <th>Actor</th>
            <th>On behalf of</th>
            <th>Action</th>
            <th>Decision</th>
            <th>Reason</th>
            <th>Score changes</th>
            <th>Summary</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => {
            const changes = scoreChangesOf(r);
            return (
              <tr key={r.id} className={r.decision === "denied" ? "row-denied" : undefined}>
                <td>{formatDate(r.ts)}</td>
                <td>
                  {r.actor_display} <span className="muted">({r.actor_kind})</span>
                </td>
                <td title={r.on_behalf_of ?? undefined}>{shortId(r.on_behalf_of)}</td>
                <td>{r.action}</td>
                <td>{r.decision}</td>
                <td>{r.reason_code ?? "—"}</td>
                <td>
                  {changes.length === 0
                    ? "—"
                    : changes.map((c, i) => (
                        <div key={i}>
                          {shortId(c.criterion_id)}: {c.before} → {c.after}
                        </div>
                      ))}
                </td>
                <td>{summary(r.result_summary) || summary(r.args_redacted) || "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
