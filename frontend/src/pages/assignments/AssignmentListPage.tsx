import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { contentRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";

export function AssignmentListPage() {
  const { courseId = "" } = useParams();
  const { api, state: auth } = useAuth();
  const isInstructor = auth.status === "signed_in" && auth.me.role === "instructor";
  const loader = useCallback(() => contentRoutes(api).listAssignments(courseId), [api, courseId]);
  const { state } = useLoad(loader);
  const base = `/courses/${encodeURIComponent(courseId)}/assignments`;

  return (
    <section>
      <div className="page-head">
        <h1>Assignments</h1>
        {isInstructor && (
          <Link className="button-link" to={`${base}/new`}>
            New assignment
          </Link>
        )}
      </div>
      {state.status === "loading" && <p className="muted">Loading…</p>}
      {state.status === "error" && <ErrorNotice error={state.error} />}
      {state.status === "ok" && state.data.length === 0 && <p>No assignments yet.</p>}
      {state.status === "ok" && state.data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              {isInstructor && <th>Status</th>}
              <th>Due</th>
              {isInstructor && <th>Grading</th>}
            </tr>
          </thead>
          <tbody>
            {state.data.map((a) => (
              <tr key={a.id}>
                <td>
                  <Link to={`${base}/${encodeURIComponent(a.id)}`}>{a.title}</Link>
                </td>
                {isInstructor && <td>{a.status === "published" ? "Published" : "Draft"}</td>}
                <td>{formatDate(a.due_at)}</td>
                {isInstructor && (
                  <td>{a.status === "published" ? <Link to={`${base}/${encodeURIComponent(a.id)}/review`}>Review grades</Link> : "—"}</td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
