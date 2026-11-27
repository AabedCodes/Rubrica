import { useCallback, useState } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { oversightRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";
import type { Draft, DraftAnswerKeyPayload, DraftAssignmentPayload } from "../../types/oversight";

const KIND: Record<Draft["kind"], string> = { assignment: "Assignment", answer_key: "Answer key", rubric: "Rubric" };

/** What accepting a draft does, in plain words (C25). */
export function draftEffect(d: Draft): string {
  if (d.kind === "assignment") {
    const pl = d.payload as DraftAssignmentPayload;
    return `Accepting creates a new DRAFT assignment "${pl.title}" with ${pl.criteria.length} criteria. Nothing is published and students see nothing until you publish it yourself.`;
  }
  const pl = d.payload as DraftAnswerKeyPayload;
  return `Accepting replaces the answer key of "${pl.assignment_title}" with these ${pl.entries.length} entries. Objective marking and the answer-key check use it from then on. This needs your authenticator code.`;
}

export function DraftsPage() {
  const { courseId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(() => oversightRoutes(api).drafts(courseId), [api, courseId]);
  const { state } = useLoad(loader);
  return (
    <section>
      <h1>Drafts from the AI assistant</h1>
      <p className="muted">The instructor agent can only draft. Nothing here takes effect until you accept it.</p>
      {state.status === "loading" && <p className="muted">Loading…</p>}
      {state.status === "error" && <ErrorNotice error={state.error} />}
      {state.status === "ok" && state.data.length === 0 && <p>No drafts.</p>}
      {state.status === "ok" && state.data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Kind</th>
              <th>Created</th>
              <th>Status</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {state.data.map((d) => (
              <tr key={d.id}>
                <td>{KIND[d.kind]}</td>
                <td>{formatDate(d.created_at)}</td>
                <td>{d.status}</td>
                <td>
                  <Link to={`/courses/${encodeURIComponent(courseId)}/drafts/${encodeURIComponent(d.id)}`}>Review draft</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/** Confirmation screen for a draft (C25): the exact content that would take effect, from the database. */
export function DraftConfirmPage() {
  const { courseId = "", draftId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(() => oversightRoutes(api).draft(draftId), [api, draftId]);
  const { state, reload } = useLoad(loader);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const d = state.data;
  const act = (accept: boolean) => {
    setBusy(true);
    setError(null);
    const r = oversightRoutes(api);
    (accept ? r.acceptDraft(d.id) : r.rejectDraft(d.id))
      .then(() => reload())
      .catch((err: unknown) => setError(err))
      .finally(() => setBusy(false));
  };

  return (
    <section>
      <p>
        <Link to={`/courses/${encodeURIComponent(courseId)}/drafts`}>← Back to drafts</Link>
      </p>
      <div className="page-head">
        <h1>{KIND[d.kind]} draft</h1>
        <span className="badge">{d.status}</span>
      </div>
      <section aria-label="Drafted by the AI assistant" className="box box-ai">
        <span className="label-ai">Drafted by the AI assistant ({d.created_by_agent}): check every line</span>
        {d.kind === "assignment" ? <AssignmentPayload p={d.payload as DraftAssignmentPayload} /> : <KeyPayload p={d.payload as DraftAnswerKeyPayload} />}
      </section>
      <section aria-label="Decision">
        <h2>Decision</h2>
        {error !== null && <ErrorNotice error={error} />}
        {d.status === "pending" ? (
          <>
            <p className="effect">{draftEffect(d)}</p>
            <div className="actions actions-left">
              <button type="button" className="primary" disabled={busy} onClick={() => act(true)}>
                Accept draft
              </button>
              <button type="button" disabled={busy} onClick={() => act(false)}>
                Reject draft
              </button>
            </div>
          </>
        ) : (
          <p>This draft was {d.status}.</p>
        )}
      </section>
    </section>
  );
}

function AssignmentPayload({ p }: { p: DraftAssignmentPayload }) {
  return (
    <>
      <h3>{p.title}</h3>
      <p className="prewrap">{p.instructions}</p>
      <table className="table compact">
        <thead>
          <tr>
            <th>Criterion</th>
            <th>Kind</th>
            <th>Max</th>
          </tr>
        </thead>
        <tbody>
          {p.criteria.map((c, i) => (
            <tr key={i}>
              <td>{c.label}</td>
              <td>{c.kind}</td>
              <td>{c.max_points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function KeyPayload({ p }: { p: DraftAnswerKeyPayload }) {
  return (
    <>
      <h3>Answer key for {p.assignment_title}</h3>
      <table className="table compact">
        <thead>
          <tr>
            <th>Criterion</th>
            <th>Key text</th>
            <th>Expected</th>
          </tr>
        </thead>
        <tbody>
          {p.entries.map((e) => (
            <tr key={e.criterion_id}>
              <td>{e.label}</td>
              <td className="prewrap">{e.content}</td>
              <td>{e.expected ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
