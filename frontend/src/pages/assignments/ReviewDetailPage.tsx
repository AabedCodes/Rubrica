import { useCallback, useState } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { ExtractedTextView } from "../../components/ExtractedTextView";
import { FLAG_EXPLANATIONS, FLAG_LABELS } from "../../components/GradeBits";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { gradingRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import type { CitationVerdict, CriterionReview, ProposedGradeDetail } from "../../types/grading";

const VERDICT_LABELS: Record<CitationVerdict, string> = {
  supports: "Supports the claim",
  does_not_support: "Does not support the claim",
  unrelated: "Unrelated to the claim",
  unreadable: "Page could not be read",
};

/** Parses an edited score: a number between 0 and the maximum, in steps of 0.5 (§7). */
export function parseScore(value: string, max: number): number | null {
  if (value.trim() === "") return null;
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 && n <= max && (n * 2) % 1 === 0 ? n : null;
}

/** Score changes the instructor made, criterion ID → new score; null if any edit is invalid. */
export function scoreChanges(criteria: readonly CriterionReview[], edits: Readonly<Record<string, string>>): Record<string, number> | null {
  const out: Record<string, number> = {};
  for (const c of criteria) {
    const raw = edits[c.criterion_id];
    if (raw === undefined) continue;
    const n = parseScore(raw, c.max_points);
    if (n === null) return null;
    if (n !== c.proposed) out[c.criterion_id] = n;
  }
  return out;
}

/**
 * Review screen for one proposed grade (A5, C36, C05; T-04, T-37).
 *
 * Left: the text exactly as the grader read it, hidden characters marked.
 * Right: per criterion, both attempts, an editable proposed score, the AI's
 * feedback (SafeMarkdown, labelled) and the quotes it relied on. Below:
 * citations and what each flag means. Flagged grades can only be approved here.
 */
export function ReviewDetailPage() {
  const { courseId = "", assignmentId = "", proposedGradeId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(async () => {
    const routes = gradingRoutes(api);
    const detail = await routes.proposedGrade(proposedGradeId);
    const extracted = await routes.extractedText(detail.submission_id);
    return { detail, text: extracted.text };
  }, [api, proposedGradeId]);
  const { state, reload } = useLoad(loader);

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const back = `/courses/${encodeURIComponent(courseId)}/assignments/${encodeURIComponent(assignmentId)}/review`;
  return (
    <section>
      <p>
        <Link to={back}>← Back to the review list</Link>
      </p>
      {/* key: start a fresh form whenever the grade reloads (after approval). */}
      <ReviewDetail key={`${state.data.detail.id}-${state.data.detail.status}`} detail={state.data.detail} text={state.data.text} onApproved={reload} />
    </section>
  );
}

function ReviewDetail({ detail, text, onApproved }: { detail: ProposedGradeDetail; text: string; onApproved: () => void }) {
  const { api } = useAuth();
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const pending = detail.status === "pending";
  const changes = scoreChanges(detail.criteria, edits);
  const newTotal =
    changes === null ? null : detail.criteria.reduce((sum, c) => sum + (changes[c.criterion_id] ?? c.proposed), 0);
  const changedCount = changes ? Object.keys(changes).length : 0;

  return (
    <>
      <div className="page-head">
        <h1>
          {detail.student.display_name}: {detail.assignment_title}
        </h1>
        <span className={`badge ${detail.status === "released" ? "badge-ok" : ""}`}>{detail.status}</span>
      </div>

      {detail.flags.length > 0 && (
        <section aria-label="Flags" className="flags-box">
          <h2>Why this grade is flagged</h2>
          <ul>
            {detail.flags.map((f) => (
              <li key={f}>
                <span className="badge badge-flag">{FLAG_LABELS[f]}</span> {FLAG_EXPLANATIONS[f]}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="review-grid">
        <ExtractedTextView text={text} />

        <section aria-label="Scores">
          <h2>Scores</h2>
          {detail.criteria.map((c) => {
            const raw = edits[c.criterion_id] ?? String(c.proposed);
            const parsed = parseScore(raw, c.max_points);
            const changed = parsed !== null && parsed !== c.proposed;
            return (
              <article key={c.criterion_id} className="card criterion-review" aria-label={c.label}>
                <h3>{c.label}</h3>
                <table className="table compact">
                  <thead>
                    <tr>
                      <th>Max</th>
                      <th>Attempt 1</th>
                      <th>Attempt 2</th>
                      <th>Proposed</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{c.max_points}</td>
                      <td>{c.attempt1}</td>
                      <td>{c.attempt2}</td>
                      <td>
                        <input
                          type="number"
                          aria-label={`Proposed score for ${c.label}`}
                          min={0}
                          max={c.max_points}
                          step={0.5}
                          value={raw}
                          disabled={!pending}
                          aria-invalid={parsed === null}
                          onChange={(e) => setEdits((x) => ({ ...x, [c.criterion_id]: e.target.value }))}
                        />
                      </td>
                    </tr>
                  </tbody>
                </table>
                {parsed === null && (
                  <p className="error" role="alert">
                    Enter a score from 0 to {c.max_points} in steps of 0.5.
                  </p>
                )}
                {changed && <p className="changed">Changed from {c.proposed} to {parsed}. The change is audited.</p>}

                {c.objective ? (
                  <p>
                    Student's answer: <strong>{c.objective.answer ?? "no answer"}</strong> · Expected:{" "}
                    <strong>{c.objective.expected}</strong> · Marked by code: <strong>{c.objective.mark}</strong>
                  </p>
                ) : (
                  <>
                    {c.feedback && (
                      <div className="ai-box">
                        <span className="label-ai">Written by the AI grader</span>
                        <SafeMarkdown text={c.feedback} />
                      </div>
                    )}
                    {c.quotes.length > 0 && (
                      <div>
                        <span className="label-ai">Quotes the grader relied on</span>
                        <ul className="quotes">
                          {c.quotes.map((q, i) => (
                            <li key={i}>
                              <q>{q.text}</q>
                              {!q.found && <span className="badge badge-flag"> {FLAG_LABELS.quote_not_found}</span>}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                )}
              </article>
            );
          })}
        </section>
      </div>

      <section aria-label="Citations">
        <h2>Citations</h2>
        {detail.citations.length === 0 ? (
          <p className="muted">The submission cites no web pages.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Address (not a link)</th>
                <th>Claim</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody>
              {detail.citations.map((c, i) => (
                <tr key={i} className={c.verdict === "supports" ? undefined : "row-flagged"}>
                  {/* Student-supplied URL shown as text, never as a clickable link. */}
                  <td>
                    <code>{c.url}</code>
                  </td>
                  <td>{c.claim}</td>
                  <td>{VERDICT_LABELS[c.verdict]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section aria-label="Decision">
        <h2>Decision</h2>
        <p>
          Total: <strong>{newTotal ?? "—"}</strong> / {detail.max_total}
          {changedCount > 0 && ` (proposed ${detail.total}; ${changedCount} criterion score${changedCount === 1 ? "" : "s"} changed)`}
        </p>
        {message && <p role="status">{message}</p>}
        {error !== null && <ErrorNotice error={error} />}
        {pending ? (
          <button
            type="button"
            className="primary"
            disabled={busy || changes === null}
            onClick={() => {
              if (!changes) return;
              setBusy(true);
              setError(null);
              gradingRoutes(api)
                .approve({
                  proposed_grade_ids: [detail.id],
                  score_changes: changedCount > 0 ? { [detail.id]: changes } : undefined,
                })
                .then(() => {
                  setMessage("Approved and released.");
                  onApproved();
                })
                .catch((err: unknown) => setError(err))
                .finally(() => setBusy(false));
            }}
          >
            {changedCount > 0 ? "Approve with changes and release" : "Approve and release"}
          </button>
        ) : (
          <p className="muted">This grade is {detail.status}; it can no longer be changed here.</p>
        )}
      </section>
    </>
  );
}
