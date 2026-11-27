import type { ReleasedGrade } from "../types/content";
import type { GradeFlag } from "../types/grading";
import { formatDate } from "../rubric";
import { SafeMarkdown } from "./SafeMarkdown";

/** Short labels for the §7 flags (C36). A5 adds the one-line explanations. */
export const FLAG_LABELS: Record<GradeFlag, string> = {
  full_marks: "Full marks",
  disagreement: "Attempts disagree",
  outlier: "Outlier",
  quote_not_found: "Quote not found",
  citation_not_supported: "Citation not supported",
  feedback_contains_key_text: "Feedback may contain key text",
};

/** One-line explanations shown on the review screen (A5, C36). full_marks is the plan's wording. */
export const FLAG_EXPLANATIONS: Record<GradeFlag, string> = {
  full_marks: "Every criterion at maximum; check that the answer earns it.",
  disagreement: "The two grading attempts differ by more than one point on a criterion; read the answer yourself.",
  outlier: "The total is more than two standard deviations from this assignment's mean.",
  quote_not_found: "The grader quoted text that isn't in the submission, so its reasoning may not rest on the answer.",
  citation_not_supported: "A cited web page doesn't support the claim it is cited for.",
  feedback_contains_key_text: "The feedback may repeat the answer key; check it before releasing (C23).",
};

export function FlagBadges({ flags }: { flags: readonly GradeFlag[] }) {
  if (flags.length === 0) return <span className="muted">none</span>;
  return (
    <span className="badges">
      {flags.map((f) => (
        <span key={f} className="badge badge-flag">
          {FLAG_LABELS[f]}
        </span>
      ))}
    </span>
  );
}

/** A student's released grade. Feedback is model-written, so it goes through SafeMarkdown (C07). */
export function ReleasedGradeView({ grade }: { grade: ReleasedGrade }) {
  return (
    <section aria-label="Your grade" className="grade">
      <h3>
        Grade: {grade.total} / {grade.max_total}
      </h3>
      <p className="muted">Released {formatDate(grade.released_at)}. Your instructor approved this grade.</p>
      <table className="table">
        <thead>
          <tr>
            <th>Criterion</th>
            <th>Score</th>
            <th>Feedback</th>
          </tr>
        </thead>
        <tbody>
          {grade.criteria.map((c) => (
            <tr key={c.criterion_id}>
              <td>{c.label}</td>
              <td>
                {c.score} / {c.max_points}
              </td>
              <td>
                {c.feedback ? (
                  <>
                    <span className="label-ai">Written by the AI grader</span>
                    <SafeMarkdown text={c.feedback} />
                  </>
                ) : (
                  <span className="muted">{c.kind === "objective" ? "Marked automatically" : "No feedback"}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
