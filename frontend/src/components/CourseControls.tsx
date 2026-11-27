import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { oversightRoutes } from "../endpoints";
import { formatDate } from "../rubric";
import type { CourseControls } from "../types/oversight";

interface ControlsValue {
  controls: CourseControls | null;
  reload: () => void;
}

const ControlsContext = createContext<ControlsValue>({ controls: null, reload: () => undefined });

/** Loads the course's pause state (C30) once per course, shared by the banner and the settings page. */
export function ControlsProvider({ courseId, children }: { courseId: string; children: ReactNode }) {
  const { api } = useAuth();
  const [controls, setControls] = useState<CourseControls | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    oversightRoutes(api)
      .controls(courseId)
      .then((c) => {
        if (!cancelled) setControls(c);
      })
      .catch(() => {
        if (!cancelled) setControls(null);
      });
    return () => {
      cancelled = true;
    };
  }, [api, courseId, version]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  const value = useMemo(() => ({ controls, reload }), [controls, reload]);
  return <ControlsContext.Provider value={value}>{children}</ControlsContext.Provider>;
}

export function useControls(): ControlsValue {
  return useContext(ControlsContext);
}

/** Shown on every course page while agents are paused (C30, plan A7). */
export function PauseBanner({ role }: { role: "student" | "instructor" }) {
  const { controls } = useControls();
  if (!controls?.agents_paused) return null;
  return (
    <div className="banner banner-paused" role="status">
      {role === "instructor" ? (
        <>
          <strong>AI agents are paused for this course</strong>
          {controls.paused_by && ` by ${controls.paused_by.display_name}`}
          {controls.paused_at && ` since ${formatDate(controls.paused_at)}`}. Reason: {controls.reason}. Grading runs send
          submissions to the manual queue until you resume.
        </>
      ) : (
        <>Grading may take longer than usual. You can still submit your work.</>
      )}
    </div>
  );
}
