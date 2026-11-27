import { useCallback, useState } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { ExtractedTextView } from "../../components/ExtractedTextView";
import { contentRoutes, gradingRoutes, oversightRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";
import type { ManualQueueItem } from "../../types/oversight";
import { parseScore } from "../assignments/ReviewDetailPage";

/** Reason codes in plain words (plan A7). */
export const REASONS: Record<ManualQueueItem["reason_code"], string> = {
  paused: "Grading paused",
  validator_rejected: "Grader output failed validation",
  step_limit: "Step limit reached",
  budget_exceeded: "Model budget used up",
  grader_error: "Grader error",
};

export function ManualQueuePage() {
  const { courseId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(() => oversightRoutes(api).manualQueue(courseId), [api, courseId]);
  const { state } = useLoad(loader);
  return (
    <section>
      <h1>Manual queue</h1>
      <p className="muted">Submissions the AI grader didn't grade. You grade these by hand.</p>
      {state.status === "loading" && <p className="muted">Loading…</p>}
      {state.status === "error" && <ErrorNotice error={state.error} />}
      {state.status === "ok" && state.data.length === 0 && <p>The queue is empty.</p>}
      {state.status === "ok" && state.data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Assignment</th>
              <th>Why</th>
              <th>Since</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {state.data.map((q) => (
              <tr key={q.id}>
                <td>
                  <Link to={`/courses/${encodeURIComponent(courseId)}/manual-queue/${encodeURIComponent(q.id)}`}>{q.student.display_name}</Link>
                </td>
                <td>{q.assignment_title}</td>
                <td>{REASONS[q.reason_code] ?? q.reason_code}</td>
                <td>{formatDate(q.created_at)}</td>
                <td>{q.resolved_at ? "Graded" : "Waiting"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/** One manual-queue item: the extracted text and a rubric form; submitting releases the grade (D3). */
export function ManualItemPage() {
  const { courseId = "", queueId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(async () => {
    const item = (await oversightRoutes(api).manualQueue(courseId)).find((q) => q.id === queueId);
    if (!item) throw new Error("not in queue");
    const [assignment, text] = await Promise.all([
      contentRoutes(api).getAssignment(item.assignment_id),
      gradingRoutes(api).extractedText(item.submission_id),
    ]);
    return { item, assignment, text: text.text };
  }, [api, courseId, queueId]);
  const { state, reload } = useLoad(loader);
  const [scores, setScores] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const { item, assignment, text } = state.data;
  const parsed = assignment.criteria.map((c) => ({ c, n: parseScore(scores[c.id] ?? "", c.max_points) }));
  const complete = parsed.every((x) => x.n !== null);
  const total = parsed.reduce((s, x) => s + (x.n ?? 0), 0);

  return (
    <section>
      <p>
        <Link to={`/courses/${encodeURIComponent(courseId)}/manual-queue`}>← Back to the manual queue</Link>
      </p>
      <h1>
        {item.student.display_name}: {item.assignment_title}
      </h1>
      <p>
        Why it's here: <strong>{REASONS[item.reason_code] ?? item.reason_code}</strong>
      </p>
      <div className="review-grid">
        <ExtractedTextView text={text} />
        <section aria-label="Your scores">
          <h2>Your scores</h2>
          {item.resolved_at ? (
            <p>Graded and released on {formatDate(item.resolved_at)}.</p>
          ) : (
            <form
              noValidate
              onSubmit={(event) => {
                event.preventDefault();
                if (!complete) return;
                setBusy(true);
                setError(null);
                const body = Object.fromEntries(parsed.map(({ c, n }) => [c.id, n!]));
                oversightRoutes(api)
                  .resolve(item.id, { scores: body })
                  .then(() => reload())
                  .catch((err: unknown) => setError(err))
                  .finally(() => setBusy(false));
              }}
            >
              {parsed.map(({ c, n }) => (
                <label key={c.id}>
                  {c.label} (max {c.max_points})
                  <input
                    type="number"
                    min={0}
                    max={c.max_points}
                    step={0.5}
                    value={scores[c.id] ?? ""}
                    aria-invalid={(scores[c.id] ?? "") !== "" && n === null}
                    onChange={(e) => setScores((s) => ({ ...s, [c.id]: e.target.value }))}
                  />
                  {(scores[c.id] ?? "") !== "" && n === null && (
                    <span className="error" role="alert">
                      From 0 to {c.max_points} in steps of 0.5.
                    </span>
                  )}
                </label>
              ))}
              <p className="effect">
                Submitting releases this grade ({complete ? total : "—"} / {assignment.criteria.reduce((s, c) => s + c.max_points, 0)}) to the
                student. The decision is audited.
              </p>
              {error !== null && <ErrorNotice error={error} />}
              <button type="submit" className="primary" disabled={busy || !complete}>
                Release my grade
              </button>
            </form>
          )}
        </section>
      </div>
    </section>
  );
}
