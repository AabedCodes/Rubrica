import { useCallback, useState } from "react";
import { Link } from "react-router";
import { ApiError } from "../../api";
import { useAuth } from "../../auth/AuthContext";
import { AnswerKeyEditor } from "../../components/AnswerKeyEditor";
import { ErrorNotice } from "../../components/ErrorNotice";
import { RubricEditor } from "../../components/RubricEditor";
import { contentRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";

export function InstructorAssignmentPage({ courseId, assignmentId }: { courseId: string; assignmentId: string }) {
  const { api } = useAuth();
  const routes = contentRoutes(api);
  const loader = useCallback(async () => {
    const r = contentRoutes(api);
    const assignment = await r.getAssignment(assignmentId);
    const key = await r.getAnswerKey(assignmentId).catch((err: unknown) => {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    });
    return { assignment, key };
  }, [api, assignmentId]);
  const { state, reload } = useLoad(loader);
  const [actionError, setActionError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const { assignment: a, key } = state.data;
  const published = a.status === "published";
  const reviewPath = `/courses/${encodeURIComponent(courseId)}/assignments/${encodeURIComponent(a.id)}/review`;

  return (
    <section>
      <div className="page-head">
        <h1>{a.title}</h1>
        <span className={`badge ${published ? "badge-ok" : ""}`}>{published ? "Published" : "Draft"}</span>
      </div>
      <p>Due {formatDate(a.due_at)}</p>
      <p className="prewrap">{a.instructions}</p>

      <h2>Rubric</h2>
      <RubricEditor
        key={`rubric-${a.version}`}
        criteria={a.criteria}
        readOnly={published}
        onSave={async (criteria) => {
          await routes.putRubric(a.id, { criteria });
          reload();
        }}
      />

      <h2>Answer key</h2>
      <p className="muted">Never shown to students (T-01). Objective criteria are marked by code against it (C20).</p>
      <AnswerKeyEditor key={`key-${a.version}`} criteria={a.criteria} answerKey={key} onSave={(entries) => routes.putAnswerKey(a.id, { entries })} />

      <h2>Publish and grade</h2>
      {actionError !== null && <ErrorNotice error={actionError} />}
      {!published ? (
        <>
          <p className="muted">Publishing shows the assignment to students. It needs your authenticator code (C28).</p>
          <button
            type="button"
            className="primary"
            disabled={busy || a.criteria.length === 0}
            onClick={() => {
              setBusy(true);
              setActionError(null);
              routes
                .publish(a.id)
                .then(() => reload())
                .catch((err: unknown) => setActionError(err))
                .finally(() => setBusy(false));
            }}
          >
            Publish assignment
          </button>
        </>
      ) : (
        <p>
          <Link to={reviewPath}>Start grading and review proposed grades</Link>
        </p>
      )}
    </section>
  );
}
