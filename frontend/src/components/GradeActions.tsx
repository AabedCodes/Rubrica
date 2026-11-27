import { useState } from "react";
import { Link } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { studentRoutes } from "../endpoints";
import { MAX_APPEAL_CHARS } from "../types/student";
import { ErrorNotice } from "./ErrorNotice";

/**
 * Under a released grade (A6): "Ask about this grade" opens the chat with the
 * question filled in; "Appeal" opens a form. The appeal is the student's own
 * text; the instructor decides it on a confirmation screen (C25, A7).
 */
export function GradeActions({ courseId, submissionId, assignmentTitle }: { courseId: string; submissionId: string; assignmentTitle: string }) {
  const { api } = useAuth();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const question = `Why did I get this grade on "${assignmentTitle}"?`;

  return (
    <div className="grade-actions">
      <div className="actions actions-left">
        <Link className="button-link" to={`/courses/${encodeURIComponent(courseId)}/chat?q=${encodeURIComponent(question)}`}>
          Ask about this grade
        </Link>
        {!sent && (
          <button type="button" onClick={() => setOpen((o) => !o)}>
            {open ? "Cancel appeal" : "Appeal"}
          </button>
        )}
      </div>
      {sent && <p role="status">Appeal sent. Your instructor will review it; your grade only changes if they accept a change.</p>}
      {open && !sent && (
        <form
          aria-label="Appeal"
          onSubmit={(event) => {
            event.preventDefault();
            const text = reason.trim();
            if (!text) return;
            setBusy(true);
            setError(null);
            studentRoutes(api)
              .openAppeal(submissionId, { reason_text: text })
              .then(() => setSent(true))
              .catch((err: unknown) => setError(err))
              .finally(() => setBusy(false));
          }}
        >
          <label>
            Why should your grade change?
            <textarea rows={4} maxLength={MAX_APPEAL_CHARS} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <p className="muted">
            {reason.length} / {MAX_APPEAL_CHARS} characters
          </p>
          {error !== null && <ErrorNotice error={error} />}
          <button type="submit" className="primary" disabled={busy || !reason.trim()}>
            Send appeal
          </button>
        </form>
      )}
    </div>
  );
}
