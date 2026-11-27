import { useCallback, useState } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { ExtractedTextView } from "../../components/ExtractedTextView";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { gradingRoutes, oversightRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";
import type { GradeChangeProposal } from "../../types/oversight";

/** Plain description of what accepting does, built from the database values only. */
export function acceptEffect(p: GradeChangeProposal): string {
  const changed = p.criteria.filter((c) => c.current !== c.proposed);
  if (changed.length === 0) return "Accepting changes no score.";
  const parts = changed.map((c) => `${c.label.split(".")[0]} from ${c.current} to ${c.proposed}`);
  return `Accepting changes ${parts.join(" and ")}, so the released total goes from ${p.current_total} to ${p.proposed_total} out of ${p.max_total}. The student sees the new grade, and the change is audited.`;
}

/**
 * Confirmation screen for an instructor-agent grade-change proposal (C25, T-02).
 * Every number comes from the database response, never from the agent's text.
 * The appeal is the student's words and the rationale is the AI's; both are
 * labelled. Accept and Reject both need re-auth (§10 decide).
 */
export function ProposalConfirmPage() {
  const { courseId = "", proposalId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(() => oversightRoutes(api).proposal(proposalId), [api, proposalId]);
  const { state, reload } = useLoad(loader);
  const [showText, setShowText] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const p = state.data;
  const pending = p.status === "pending";

  const decide = (decision: "accept" | "reject") => {
    setBusy(true);
    setError(null);
    oversightRoutes(api)
      .decide(p.id, { decision })
      .then(() => reload())
      .catch((err: unknown) => setError(err))
      .finally(() => setBusy(false));
  };

  return (
    <section>
      <p>
        <Link to={`/courses/${encodeURIComponent(courseId)}/appeals`}>← Back to appeals</Link>
      </p>
      <div className="page-head">
        <h1>
          Grade-change proposal: {p.appeal.student.display_name}, {p.assignment_title}
        </h1>
        <span className="badge">{p.status}</span>
      </div>

      <h2>Scores (from the database)</h2>
      <table className="table" aria-label="Current and proposed scores">
        <thead>
          <tr>
            <th>Criterion</th>
            <th>Max</th>
            <th>Current (released)</th>
            <th>Proposed</th>
          </tr>
        </thead>
        <tbody>
          {p.criteria.map((c) => (
            <tr key={c.criterion_id} className={c.current !== c.proposed ? "row-flagged" : undefined}>
              <td>{c.label}</td>
              <td>{c.max_points}</td>
              <td>{c.current}</td>
              <td>{c.proposed}</td>
            </tr>
          ))}
          <tr>
            <th>Total</th>
            <td>{p.max_total}</td>
            <td>{p.current_total}</td>
            <td>{p.proposed_total}</td>
          </tr>
        </tbody>
      </table>

      <div className="two-col">
        <section aria-label="Written by the student" className="box box-student">
          <span className="label-ai">Written by the student</span>
          <p className="prewrap">{p.appeal.reason_text}</p>
          <p className="muted">Appeal opened {formatDate(p.appeal.created_at)}.</p>
        </section>
        <section aria-label="Written by the AI assistant" className="box box-ai">
          <span className="label-ai">Written by the AI assistant: check it against the submission</span>
          <SafeMarkdown text={p.rationale} />
        </section>
      </div>

      <p>
        <button type="button" onClick={() => setShowText((s) => !s)}>
          {showText ? "Hide" : "Show"} the submission's extracted text
        </button>
      </p>
      {showText && <SubmissionText submissionId={p.submission_id} />}

      <section aria-label="Decision">
        <h2>Decision</h2>
        {error !== null && <ErrorNotice error={error} />}
        {pending ? (
          <>
            <p className="effect">{acceptEffect(p)}</p>
            <p className="muted">Rejecting leaves the released grade as it is. Both need your authenticator code.</p>
            <div className="actions actions-left">
              <button type="button" className="primary" disabled={busy} onClick={() => decide("accept")}>
                Accept proposal
              </button>
              <button type="button" disabled={busy} onClick={() => decide("reject")}>
                Reject proposal
              </button>
            </div>
          </>
        ) : (
          <p>
            {p.status === "accepted" ? "Accepted" : "Rejected"}
            {p.decided_by && ` by ${p.decided_by.display_name}`}
            {p.decided_at && ` on ${formatDate(p.decided_at)}`}.
          </p>
        )}
      </section>
    </section>
  );
}

function SubmissionText({ submissionId }: { submissionId: string }) {
  const { api } = useAuth();
  const loader = useCallback(() => gradingRoutes(api).extractedText(submissionId), [api, submissionId]);
  const { state } = useLoad(loader);
  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  return <ExtractedTextView text={state.data.text} />;
}
