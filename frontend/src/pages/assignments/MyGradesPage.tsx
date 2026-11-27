import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { ApiError } from "../../api";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { ReleasedGradeView } from "../../components/GradeBits";
import { contentRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";

/**
 * Student's released grades (A2). Uses §10 GET /assignments/{id}/my-submission
 * per published assignment, which only carries a grade once released (R10).
 */
export function MyGradesPage() {
  const { courseId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(async () => {
    const r = contentRoutes(api);
    const assignments = await r.listAssignments(courseId);
    return Promise.all(
      assignments.map(async (assignment) => ({
        assignment,
        mine: await r.mySubmission(assignment.id).catch((err: unknown) => {
          if (err instanceof ApiError && err.status === 404) return null;
          throw err;
        }),
      })),
    );
  }, [api, courseId]);
  const { state } = useLoad(loader);

  return (
    <section>
      <h1>My grades</h1>
      {state.status === "loading" && <p className="muted">Loading…</p>}
      {state.status === "error" && <ErrorNotice error={state.error} />}
      {state.status === "ok" && state.data.length === 0 && <p>No assignments yet.</p>}
      {state.status === "ok" &&
        state.data.map(({ assignment, mine }) => (
          <article key={assignment.id} className="card">
            <h2>
              <Link to={`/courses/${encodeURIComponent(courseId)}/assignments/${encodeURIComponent(assignment.id)}`}>
                {assignment.title}
              </Link>
            </h2>
            {!mine && <p className="muted">Not submitted.</p>}
            {mine && !mine.grade && <p className="muted">Submitted; not released yet.</p>}
            {mine?.grade && <ReleasedGradeView grade={mine.grade} />}
          </article>
        ))}
    </section>
  );
}
