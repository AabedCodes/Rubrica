import { useCallback } from "react";
import { Link, useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { oversightRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";

const STATUS: Record<string, string> = {
  open: "Open: no proposal yet",
  proposed: "AI assistant proposed a change: your decision needed",
  decided: "Decided",
};

/** Appeals for the course (C37 list_appeals, A7). */
export function AppealsPage() {
  const { courseId = "" } = useParams();
  const { api } = useAuth();
  const loader = useCallback(() => oversightRoutes(api).appeals(courseId), [api, courseId]);
  const { state } = useLoad(loader);

  return (
    <section>
      <h1>Appeals</h1>
      {state.status === "loading" && <p className="muted">Loading…</p>}
      {state.status === "error" && <ErrorNotice error={state.error} />}
      {state.status === "ok" && state.data.length === 0 && <p>No appeals.</p>}
      {state.status === "ok" && state.data.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Student</th>
              <th>Assignment</th>
              <th>Opened</th>
              <th>Status</th>
              <th>Proposal</th>
            </tr>
          </thead>
          <tbody>
            {state.data.map((a) => (
              <tr key={a.id}>
                <td>{a.student.display_name}</td>
                <td>{a.assignment_title}</td>
                <td>{formatDate(a.created_at)}</td>
                <td>{STATUS[a.status] ?? a.status}</td>
                <td>
                  {a.proposal_id ? (
                    <Link to={`/courses/${encodeURIComponent(courseId)}/proposals/${encodeURIComponent(a.proposal_id)}`}>Review proposal</Link>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
