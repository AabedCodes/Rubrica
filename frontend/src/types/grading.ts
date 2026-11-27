/**
 * Grading runs and the review list (A2; routes owned by C for runs, D for
 * approve and release, 01-interfaces.md §10). Bodies are ASSUMED.
 */

/** §7 flags stored on proposed_grades.flags (C36). */
export type GradeFlag =
  | "full_marks"
  | "disagreement"
  | "outlier"
  | "quote_not_found"
  | "citation_not_supported"
  | "feedback_contains_key_text";

export type ProposedGradeStatus = "pending" | "approved" | "released" | "rejected";

/** One row of §10 GET /assignments/{id}/proposed-grades. ASSUMED body. */
export interface ProposedGradeRow {
  id: string;
  submission_id: string;
  student: { id: string; display_name: string };
  total: number;
  max_total: number;
  status: ProposedGradeStatus;
  flags: GradeFlag[];
}

/** §10 POST /assignments/{id}/grading-runs. ASSUMED response. */
export interface StartRunResponse {
  run_id: string;
  submissions: number;
}

/**
 * §10 POST /proposed-grades/approve (re-auth, C28). ASSUMED body. Score changes
 * from the review screen are added in A5. ASSUMED: approving hands the grades
 * to the release service (D3), which publishes them.
 */
export interface ApproveRequest {
  proposed_grade_ids: string[];
}

export interface ApproveResponse {
  released: number;
}
