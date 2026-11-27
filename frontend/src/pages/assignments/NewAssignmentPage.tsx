import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { contentRoutes } from "../../endpoints";

export function NewAssignmentPage() {
  const { courseId = "" } = useParams();
  const { api } = useAuth();
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [due, setDue] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <section>
      <h1>New assignment</h1>
      <p className="muted">The assignment starts as a draft. Add the rubric and answer key, then publish it.</p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const dueDate = new Date(due);
          if (Number.isNaN(dueDate.getTime())) {
            setError(new Error("due date"));
            return;
          }
          setBusy(true);
          setError(null);
          contentRoutes(api)
            .createAssignment(courseId, { title: title.trim(), instructions, due_at: dueDate.toISOString() })
            .then((a) => navigate(`/courses/${encodeURIComponent(courseId)}/assignments/${encodeURIComponent(a.id)}`))
            .catch((err: unknown) => {
              setError(err);
              setBusy(false);
            });
        }}
      >
        <label>
          Title
          <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          Instructions
          <textarea rows={5} value={instructions} onChange={(e) => setInstructions(e.target.value)} />
        </label>
        <label>
          Due
          <input type="datetime-local" required value={due} onChange={(e) => setDue(e.target.value)} />
        </label>
        {error !== null && <ErrorNotice error={error} />}
        <button type="submit" disabled={busy}>
          Create draft
        </button>
      </form>
    </section>
  );
}
