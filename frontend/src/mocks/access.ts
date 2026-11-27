/** MOCK access rules shared by the mocked routes (C29 in miniature). */
import type { MockContext } from "./http";
import type { MockAssignment } from "./state";

/**
 * Finds an assignment the caller may see. Students never see drafts, and an
 * assignment in another course is "not found" rather than "forbidden" so its
 * existence isn't revealed (same rule as E_NOT_FOUND in §5).
 */
export function visibleAssignment(ctx: MockContext, id: string | undefined): MockAssignment | null {
  const a = ctx.world.assignments.find((x) => x.id === id);
  if (!a || !ctx.enrolledIn(a.course_id)) return null;
  if (ctx.user.role === "student" && a.status !== "published") return null;
  return a;
}
