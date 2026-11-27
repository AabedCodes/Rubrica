/**
 * Chat, appeals, blog and materials (A6). Routes: §10 Chat (C), Appeals
 * (C, D), Blog (D7), Materials (D6); C6 in docs/plan/C-agent-llm-engineer.md.
 * Bodies are ASSUMED and go into the next §10 proposal (A6 worklog).
 */
import type { PersonRef } from "./oversight";

/** §10 POST /courses/{id}/chat with {message, conversation_id} (C6 plan). */
export interface ChatRequest {
  message: string;
  conversation_id: string | null;
}

/** Where a reply's information came from, with its trust label (C01, C24). */
export interface ChatSource {
  label: string;
  trust: "instructor" | "third_party" | "blog_post" | "student_comment";
}

/**
 * ASSUMED response. `reply` is model-written: render with SafeMarkdown only.
 * `notice` replaces the reply with a fixed message: `answer_key_blocked` is
 * C23's check, `agents_paused` is C30.
 */
export interface ChatResponse {
  conversation_id: string;
  reply: { text: string; sources: ChatSource[] } | null;
  notice: "answer_key_blocked" | "agents_paused" | null;
}

export const MAX_APPEAL_CHARS = 2000; // same limit as the open_appeal MCP tool (§5)

/** ASSUMED route POST /submissions/{id}/appeals: the plain-form path (plan A6: "agree with C which"). */
export interface AppealRequest {
  reason_text: string;
}

export interface Author extends PersonRef {
  role: "student" | "instructor";
}

export interface BlogComment {
  id: string;
  author: Author;
  body: string;
  created_at: string;
}

/** §10 GET /courses/{id}/blog/posts. ASSUMED body: posts with their comments. */
export interface BlogPost {
  id: string;
  author: Author;
  body: string;
  created_at: string;
  comments: BlogComment[];
}

/** ASSUMED route GET /courses/{id}/materials (instructors). §3.1 materials plus parse status (D4). */
export interface Material {
  id: string;
  title: string;
  source_kind: "instructor" | "third_party";
  status: "pending" | "published";
  parse_status: "queued" | "parsed" | "failed";
  uploaded_at: string;
}

/** ASSUMED route GET /materials/{id}/extracted-text: what ingestion will index (C04). */
export interface MaterialText {
  material_id: string;
  text: string;
}
