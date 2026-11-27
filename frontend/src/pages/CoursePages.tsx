import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { authRoutes } from "../api";
import type { Course } from "../apiTypes";
import { useAuth } from "../auth/AuthContext";
import type { CourseScreen } from "../navigation";

export function HomePage() {
  const { api } = useAuth();
  const [courses, setCourses] = useState<Course[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    authRoutes(api)
      .courses()
      .then((list) => {
        if (!cancelled) setCourses(list);
      })
      .catch(() => {
        if (!cancelled) setCourses([]);
      });
    return () => {
      cancelled = true;
    };
  }, [api]);

  return (
    <section>
      <h1>Your courses</h1>
      {courses === null && <p className="muted">Loading…</p>}
      {courses?.length === 0 && <p>You are not enrolled in any course.</p>}
      <ul className="course-list">
        {courses?.map((c) => (
          <li key={c.id}>
            <Link to={`/courses/${encodeURIComponent(c.id)}`}>
              {c.code}: {c.title}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function CourseOverviewPage() {
  const { courseId } = useParams();
  return (
    <section>
      <h1>Course overview</h1>
      <p className="muted">Course {courseId}. Pick a screen from the menu.</p>
    </section>
  );
}

/** Placeholder until the screen's own task builds it. */
export function PlaceholderPage({ screen }: { screen: CourseScreen }) {
  return (
    <section>
      <h1>{screen.label}</h1>
      <p className="muted">This screen arrives in task {screen.task}.</p>
    </section>
  );
}

export function NotAvailablePage() {
  return (
    <section>
      <h1>Not available</h1>
      <p>This screen is not available for your role.</p>
    </section>
  );
}

export function NotFoundPage() {
  return (
    <section>
      <h1>Page not found</h1>
      <p>
        <Link to="/">Back to your courses</Link>
      </p>
    </section>
  );
}
