import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router";
import type { ApiClient } from "./api";
import type { Role } from "./apiTypes";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ReauthProvider } from "./auth/ReauthProvider";
import { Layout } from "./components/Layout";
import { COURSE_SCREENS } from "./navigation";
import { CourseOverviewPage, HomePage, NotAvailablePage, NotFoundPage, PlaceholderPage } from "./pages/CoursePages";
import { AssignmentListPage } from "./pages/assignments/AssignmentListPage";
import { AssignmentPage } from "./pages/assignments/AssignmentPage";
import { MyGradesPage } from "./pages/assignments/MyGradesPage";
import { NewAssignmentPage } from "./pages/assignments/NewAssignmentPage";
import { ReviewDetailPage } from "./pages/assignments/ReviewDetailPage";
import { ReviewListPage } from "./pages/assignments/ReviewListPage";
import { LoginPage } from "./pages/LoginPage";
import { TotpPage } from "./pages/TotpPage";

/** Screens that are built; the rest show a placeholder naming their task. */
const SCREEN_ELEMENTS: Partial<Record<string, ReactNode>> = {
  assignments: <AssignmentListPage />,
  grades: <MyGradesPage />,
};

function RequireAuth({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  const location = useLocation();
  if (state.status === "loading") return <p className="muted">Loading…</p>;
  if (state.status !== "signed_in") return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

/** UI convenience only; the API enforces roles (C29). */
function RequireRole({ roles, children }: { roles: readonly Role[]; children: ReactNode }) {
  const { state } = useAuth();
  if (state.status !== "signed_in" || !roles.includes(state.me.role)) return <NotAvailablePage />;
  return children;
}

export function AppRoutes({ mockMode = false }: { mockMode?: boolean }) {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/totp" element={<TotpPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout mockMode={mockMode} />
          </RequireAuth>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="courses/:courseId" element={<CourseOverviewPage />} />
        {COURSE_SCREENS.map((screen) => (
          <Route
            key={screen.path}
            path={`courses/:courseId/${screen.path}`}
            element={<RequireRole roles={screen.roles}>{SCREEN_ELEMENTS[screen.path] ?? <PlaceholderPage screen={screen} />}</RequireRole>}
          />
        ))}
        {/* A2: assignment pages under the Assignments screen. */}
        <Route
          path="courses/:courseId/assignments/new"
          element={
            <RequireRole roles={["instructor"]}>
              <NewAssignmentPage />
            </RequireRole>
          }
        />
        <Route path="courses/:courseId/assignments/:assignmentId" element={<AssignmentPage />} />
        <Route
          path="courses/:courseId/assignments/:assignmentId/review"
          element={
            <RequireRole roles={["instructor"]}>
              <ReviewListPage />
            </RequireRole>
          }
        />
        <Route
          path="courses/:courseId/assignments/:assignmentId/review/:proposedGradeId"
          element={
            <RequireRole roles={["instructor"]}>
              <ReviewDetailPage />
            </RequireRole>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export function App({ api, mockMode = false }: { api: ApiClient; mockMode?: boolean }) {
  return (
    <AuthProvider api={api}>
      <ReauthProvider api={api}>
        <AppRoutes mockMode={mockMode} />
      </ReauthProvider>
    </AuthProvider>
  );
}
