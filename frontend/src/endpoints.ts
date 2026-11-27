/**
 * Typed wrappers for the §10 content and grading routes the screens use (A2).
 * Routes marked ASSUMED are not in 01-interfaces.md §10 yet (see the A2 worklog).
 */
import type { ApiClient } from "./api";
import type {
  AnswerKey,
  Assignment,
  AssignmentSummary,
  CreateAssignmentRequest,
  MySubmission,
  PutAnswerKeyRequest,
  PutRubricRequest,
} from "./types/content";
import type { ApproveRequest, ApproveResponse, ExtractedText, ProposedGradeDetail, ProposedGradeRow, StartRunResponse } from "./types/grading";

const enc = encodeURIComponent;

export function contentRoutes(api: ApiClient) {
  return {
    /** ASSUMED route. */
    listAssignments: (courseId: string) => api.get<AssignmentSummary[]>(`/courses/${enc(courseId)}/assignments`),
    createAssignment: (courseId: string, body: CreateAssignmentRequest) =>
      api.post<Assignment>(`/courses/${enc(courseId)}/assignments`, body),
    /** ASSUMED route. */
    getAssignment: (id: string) => api.get<Assignment>(`/assignments/${enc(id)}`),
    putRubric: (id: string, body: PutRubricRequest) => api.put<Assignment>(`/assignments/${enc(id)}/rubric`, body),
    /** ASSUMED route. */
    getAnswerKey: (id: string) => api.get<AnswerKey>(`/assignments/${enc(id)}/answer-key`),
    putAnswerKey: (id: string, body: PutAnswerKeyRequest) => api.put<AnswerKey>(`/assignments/${enc(id)}/answer-key`, body),
    /** Re-auth (C28): the client opens the modal on 401 reauth_required. */
    publish: (id: string) => api.post<Assignment>(`/assignments/${enc(id)}/publish`),
    submit: (id: string, form: FormData) => api.postForm<{ id: string }>(`/assignments/${enc(id)}/submissions`, form),
    mySubmission: (id: string) => api.get<MySubmission>(`/assignments/${enc(id)}/my-submission`),
  };
}

export function gradingRoutes(api: ApiClient) {
  return {
    startRun: (assignmentId: string) => api.post<StartRunResponse>(`/assignments/${enc(assignmentId)}/grading-runs`),
    proposedGrades: (assignmentId: string) => api.get<ProposedGradeRow[]>(`/assignments/${enc(assignmentId)}/proposed-grades`),
    /** ASSUMED route (A5). */
    proposedGrade: (id: string) => api.get<ProposedGradeDetail>(`/proposed-grades/${enc(id)}`),
    /** §10, instructor only: exactly the text the grader read (C36). */
    extractedText: (submissionId: string) => api.get<ExtractedText>(`/submissions/${enc(submissionId)}/extracted-text`),
    /** Re-auth (C28). */
    approve: (body: ApproveRequest) => api.post<ApproveResponse>("/proposed-grades/approve", body),
  };
}
