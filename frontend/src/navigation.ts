import type { Role } from "./apiTypes";

/**
 * Course-level screens and who may see them. Used for both the navigation and
 * the route guards, so the two cannot drift apart.
 *
 * Hiding a link is a convenience, not a control: the API checks the caller's
 * role and course membership on every request (C29, 01-interfaces.md §10).
 */
export interface CourseScreen {
  path: string; // relative to /courses/:courseId
  label: string;
  roles: readonly Role[];
  task: string; // the plan task that builds the screen
}

export const COURSE_SCREENS: readonly CourseScreen[] = [
  { path: "assignments", label: "Assignments", roles: ["student", "instructor"], task: "A2" },
  { path: "grades", label: "My grades", roles: ["student"], task: "A2" },
  { path: "chat", label: "Ask the assistant", roles: ["student"], task: "A6" },
  { path: "blog", label: "Blog", roles: ["student", "instructor"], task: "A6" },
  { path: "materials", label: "Materials", roles: ["instructor"], task: "A6" },
  { path: "appeals", label: "Appeals", roles: ["instructor"], task: "A7" },
  { path: "drafts", label: "AI drafts", roles: ["instructor"], task: "A7" },
  { path: "manual-queue", label: "Manual queue", roles: ["instructor"], task: "A7" },
  { path: "audit", label: "Audit log", roles: ["instructor"], task: "A7" },
  { path: "settings", label: "Course settings", roles: ["instructor"], task: "A7" },
];

export function screensFor(role: Role): CourseScreen[] {
  return COURSE_SCREENS.filter((s) => s.roles.includes(role));
}
