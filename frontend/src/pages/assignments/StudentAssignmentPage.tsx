import { useCallback, useState } from "react";
import { ApiError } from "../../api";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { GradeActions } from "../../components/GradeActions";
import { ReleasedGradeView } from "../../components/GradeBits";
import { contentRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";
import { MAX_PDF_BYTES, type Assignment, type MySubmission } from "../../types/content";

export function StudentAssignmentPage({ assignmentId }: { assignmentId: string }) {
  const { api } = useAuth();
  const loader = useCallback(async () => {
    const r = contentRoutes(api);
    const assignment = await r.getAssignment(assignmentId);
    const mine = await r.mySubmission(assignmentId).catch((err: unknown) => {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    });
    // Decided when loaded (render must stay pure); the server enforces the deadline anyway.
    const open = Date.now() <= Date.parse(assignment.due_at);
    return { assignment, mine, open };
  }, [api, assignmentId]);
  const { state, reload } = useLoad(loader);

  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status === "error") return <ErrorNotice error={state.error} />;
  const { assignment: a, mine, open } = state.data;

  return (
    <section>
      <h1>{a.title}</h1>
      <p>Due {formatDate(a.due_at)}</p>
      <p className="prewrap">{a.instructions}</p>

      <h2>Rubric</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Question</th>
            <th>Points</th>
          </tr>
        </thead>
        <tbody>
          {a.criteria.map((c) => (
            <tr key={c.id}>
              <td>{c.label}</td>
              <td>{c.max_points}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {mine && <SubmissionSummary assignment={a} mine={mine} />}
      {mine?.grade && (
        <>
          <ReleasedGradeView grade={mine.grade} />
          <GradeActions courseId={a.course_id} submissionId={mine.id} assignmentTitle={a.title} />
        </>
      )}

      {open ? (
        <>
          <h2>{mine ? "Submit again" : "Your submission"}</h2>
          {mine && <p className="muted">A new submission replaces your current one.</p>}
          <SubmissionForm assignment={a} onSubmitted={reload} />
        </>
      ) : (
        <p className="muted">Submissions are closed.</p>
      )}
    </section>
  );
}

function SubmissionSummary({ assignment, mine }: { assignment: Assignment; mine: MySubmission }) {
  return (
    <section aria-label="Your current submission">
      <h2>Submitted</h2>
      <p className="muted">
        Submitted {formatDate(mine.submitted_at)}
        {mine.file_name ? `, with file ${mine.file_name}` : ""}.{" "}
        {mine.grade ? "" : "Your grade appears here once your instructor releases it."}
      </p>
      {assignment.criteria
        .filter((c) => c.kind === "objective")
        .map((c) => (
          <p key={c.id}>
            {c.label}: <strong>{mine.objective_answers[c.id] ?? "no answer"}</strong>
          </p>
        ))}
      <pre className="submission-text">{mine.body_text}</pre>
    </section>
  );
}

function SubmissionForm({ assignment, onSubmitted }: { assignment: Assignment; onSubmitted: () => void }) {
  const { api } = useAuth();
  const objective = assignment.criteria.filter((c) => c.kind === "objective");
  const [text, setText] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <form
      aria-label="Submission"
      onSubmit={(event) => {
        event.preventDefault();
        if (fileError) return;
        const form = new FormData();
        form.set("body_text", text);
        form.set("objective_answers", JSON.stringify(answers));
        if (file) form.set("file", file);
        setBusy(true);
        setError(null);
        contentRoutes(api)
          .submit(assignment.id, form)
          .then(() => {
            setText("");
            setAnswers({});
            setFile(null);
            onSubmitted();
          })
          .catch((err: unknown) => setError(err))
          .finally(() => setBusy(false));
      }}
    >
      {objective.map((c) => (
        <label key={c.id}>
          {c.label}
          <input value={answers[c.id] ?? ""} onChange={(e) => setAnswers((a) => ({ ...a, [c.id]: e.target.value }))} />
        </label>
      ))}
      <label>
        Your answer
        <textarea rows={8} required value={text} onChange={(e) => setText(e.target.value)} />
      </label>
      <label>
        PDF (optional)
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            setFile(f);
            if (f && f.type !== "application/pdf") setFileError("Only PDF files can be attached.");
            else if (f && f.size > MAX_PDF_BYTES) setFileError("The PDF is larger than 10 MB.");
            else setFileError(null);
          }}
        />
      </label>
      {fileError && (
        <p className="error" role="alert">
          {fileError}
        </p>
      )}
      {error !== null && <ErrorNotice error={error} />}
      <button type="submit" disabled={busy || fileError !== null}>
        Submit
      </button>
    </form>
  );
}
