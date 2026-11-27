import { matchPath, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { screensFor } from "../navigation";
import { ControlsProvider, PauseBanner } from "./CourseControls";
import { CourseSwitcher } from "./CourseSwitcher";

export function Layout({ mockMode }: { mockMode: boolean }) {
  const { api, state, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const courseId = matchPath("/courses/:courseId/*", pathname)?.params.courseId;

  if (state.status !== "signed_in") return null;
  const { me } = state;

  return (
    <div className="app">
      {mockMode && (
        <div className="banner banner-mock" role="status">
          Mock API: every response is canned test data (src/mocks/). Not connected to the backend.
        </div>
      )}
      <header className="topbar">
        <NavLink to="/" className="brand">
          Rubrica
        </NavLink>
        <CourseSwitcher api={api} currentCourseId={courseId} />
        <div className="user">
          <span>
            {me.display_name} <span className="muted">({me.role})</span>
          </span>
          <button
            type="button"
            onClick={() => {
              logout().finally(() => navigate("/login", { replace: true }));
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="body">
        {courseId && (
          <nav aria-label="Course" className="sidenav">
            <ul>
              <li>
                <NavLink to={`/courses/${encodeURIComponent(courseId)}`} end>
                  Overview
                </NavLink>
              </li>
              {screensFor(me.role).map((s) => (
                <li key={s.path}>
                  <NavLink to={`/courses/${encodeURIComponent(courseId)}/${s.path}`}>{s.label}</NavLink>
                </li>
              ))}
            </ul>
          </nav>
        )}
        <main>
          {courseId ? (
            // key: fresh pause state per course (C30 banner on every course page)
            <ControlsProvider key={courseId} courseId={courseId}>
              <PauseBanner role={me.role} />
              <Outlet />
            </ControlsProvider>
          ) : (
            <Outlet />
          )}
        </main>
      </div>
    </div>
  );
}
