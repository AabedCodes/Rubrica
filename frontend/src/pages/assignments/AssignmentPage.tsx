import { useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { InstructorAssignmentPage } from "./InstructorAssignmentPage";
import { StudentAssignmentPage } from "./StudentAssignmentPage";

export function AssignmentPage() {
  const { courseId = "", assignmentId = "" } = useParams();
  const { state } = useAuth();
  if (state.status !== "signed_in") return null;
  // key: remount when the URL changes so no state leaks between assignments.
  return state.me.role === "instructor" ? (
    <InstructorAssignmentPage key={assignmentId} courseId={courseId} assignmentId={assignmentId} />
  ) : (
    <StudentAssignmentPage key={assignmentId} assignmentId={assignmentId} />
  );
}
