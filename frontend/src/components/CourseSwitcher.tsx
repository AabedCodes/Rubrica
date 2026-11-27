import { useEffect, useId, useState } from "react";
import { useNavigate } from "react-router";
import { authRoutes, type ApiClient } from "../api";
import type { Course } from "../apiTypes";

export function CourseSwitcher({ api, currentCourseId }: { api: ApiClient; currentCourseId: string | undefined }) {
  const id = useId();
  const navigate = useNavigate();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    authRoutes(api)
      .courses()
      .then((list) => {
        if (!cancelled) setCourses(list);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [api]);

  if (failed) return <span className="muted">Courses unavailable</span>;
  if (courses === null) return <span className="muted">Loading courses…</span>;

  return (
    <div className="course-switcher">
      <label htmlFor={id}>Course</label>
      <select
        id={id}
        value={currentCourseId ?? ""}
        onChange={(e) => {
          if (e.target.value) navigate(`/courses/${encodeURIComponent(e.target.value)}`);
        }}
      >
        <option value="">Choose a course</option>
        {courses.map((c) => (
          <option key={c.id} value={c.id}>
            {c.code}: {c.title}
          </option>
        ))}
      </select>
    </div>
  );
}
