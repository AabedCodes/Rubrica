import { useState } from "react";
import { useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { useControls } from "../../components/CourseControls";
import { ErrorNotice } from "../../components/ErrorNotice";
import { oversightRoutes } from "../../endpoints";

/**
 * Course settings: the pause switch for AI agents (C30; E10 builds the switch).
 * Pausing revokes the course's agent tokens; grading runs send submissions to
 * the manual queue; students can still submit. Pause and resume need re-auth.
 */
export function CourseSettingsPage() {
  const { courseId = "" } = useParams();
  const { api } = useAuth();
  const { controls, reload } = useControls();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  if (!controls) return <p className="muted">Loading…</p>;
  const run = (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    action()
      .then(() => {
        setReason("");
        reload();
      })
      .catch((err: unknown) => setError(err))
      .finally(() => setBusy(false));
  };

  return (
    <section>
      <h1>Course settings</h1>
      <h2>AI agents</h2>
      {error !== null && <ErrorNotice error={error} />}
      {controls.agents_paused ? (
        <>
          <p>
            Agents are <strong>paused</strong>. Reason: {controls.reason}
          </p>
          <p className="effect">
            Resuming lets agents act again: the chat agent answers, the instructor agent drafts, and new grading runs grade
            instead of filling the manual queue. Items already in the manual queue stay there. Needs your authenticator code.
          </p>
          <button type="button" className="primary" disabled={busy} onClick={() => run(() => oversightRoutes(api).resume(courseId))}>
            Resume AI agents
          </button>
        </>
      ) : (
        <form
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            if (!reason.trim()) return;
            run(() => oversightRoutes(api).pause(courseId, reason.trim()));
          }}
        >
          <p className="effect">
            Pausing stops every AI agent in this course at its next step: running grading moves the remaining submissions to
            the manual queue, chat and the instructor agent stop answering. Students can still submit. Needs your
            authenticator code.
          </p>
          <label>
            Reason (shown on the banner and kept in the audit log)
            <input value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} />
          </label>
          <button type="submit" className="primary" disabled={busy || !reason.trim()}>
            Pause AI agents for this course
          </button>
        </form>
      )}
    </section>
  );
}
