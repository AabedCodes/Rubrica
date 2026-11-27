import { useCallback, useState } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { FlagBadges } from "../../components/GradeBits";
import { contentRoutes, gradingRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import type { ProposedGradeRow } from "../../types/grading";

/** Flagged first, then pending before decided, then by name. */
export function sortForReview(rows: readonly ProposedGradeRow[]): ProposedGradeRow[] {
  return [...rows].sort(
    (a, b) =>
      Number(b.flags.length > 0) - Number(a.flags.length > 0) ||
      Number(b.status === "pending") - Number(a.status === "pending") ||
      a.student.display_name.localeCompare(b.student.display_name),
  );
}

/** Only unflagged pending grades can be approved in bulk; flagged ones need the detail view (C36). */
export const bulkApprovable = (row: ProposedGradeRow) => row.status === "pending" && row.flags.length === 0;

/**
 * Review list (A2; the full review screen is A5). Approving opens the re-auth
 * modal when the last TOTP entry is older than the window (C28, R10).
 */
export function ReviewListPage() {
  const { courseId = "", assignmentId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(async () => {
    const [assignment, rows] = await Promise.all([
      contentRoutes(api).getAssignment(assignmentId),
      gradingRoutes(api).proposedGrades(assignmentId),
    ]);
    return { assignment, rows: sortForReview(rows) };
  }, [api, assignmentId]);
  const { state, reload } = useLoad(loader);
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const { assignment, rows } = state.data;
  const approvable = rows.filter(bulkApprovable);
  const chosen = approvable.filter((r) => selected.has(r.id));
  const detailBase = `/courses/${encodeURIComponent(courseId)}/assignments/${encodeURIComponent(assignmentId)}/review`;

  const run = (action: () => Promise<string>) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    action()
      .then((msg) => {
        setMessage(msg);
        setSelected(new Set());
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setBusy(false));
  };

  return (
    <section>
      <h1>Review: {assignment.title}</h1>
      <div className="actions actions-left">
        <button
          type="button"
          disabled={busy || assignment.status !== "published"}
          onClick={() =>
            run(async () => {
              const r = await gradingRoutes(api).startRun(assignmentId);
              return `Grading run started for ${r.submissions} submission${r.submissions === 1 ? "" : "s"}.`;
            })
          }
        >
          Start grading run
        </button>
      </div>
      {message && <p role="status">{message}</p>}
      {error !== null && <ErrorNotice error={error} />}

      {rows.length === 0 ? (
        <p>No proposed grades yet. Start a grading run once students have submitted.</p>
      ) : (
        <>
          <p className="muted">
            Flagged grades are listed first and can only be approved from their detail view. Approving releases the grade to the
            student and needs your authenticator code.
          </p>
          <table className="table">
            <thead>
              <tr>
                <th>
                  <span className="visually-hidden">Select</span>
                </th>
                <th>Student</th>
                <th>Proposed total</th>
                <th>Flags</th>
                <th>Status</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className={r.flags.length ? "row-flagged" : undefined}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Select ${r.student.display_name}`}
                      disabled={!bulkApprovable(r)}
                      checked={selected.has(r.id)}
                      onChange={(e) =>
                        setSelected((s) => {
                          const next = new Set(s);
                          if (e.target.checked) next.add(r.id);
                          else next.delete(r.id);
                          return next;
                        })
                      }
                    />
                  </td>
                  <td>{r.student.display_name}</td>
                  <td>
                    {r.total} / {r.max_total}
                  </td>
                  <td>
                    <FlagBadges flags={r.flags} />
                  </td>
                  <td>{r.status}</td>
                  <td>
                    <Link to={`${detailBase}/${encodeURIComponent(r.id)}`}>Open</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="actions actions-left">
            <button
              type="button"
              className="primary"
              disabled={busy || chosen.length === 0}
              onClick={() =>
                run(async () => {
                  const r = await gradingRoutes(api).approve({ proposed_grade_ids: chosen.map((c) => c.id) });
                  return `Approved and released ${r.released} grade${r.released === 1 ? "" : "s"}.`;
                })
              }
            >
              Approve selected ({chosen.length})
            </button>
          </div>
        </>
      )}
    </section>
  );
}
