import { useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { studentRoutes } from "../../endpoints";
import type { ChatResponse, ChatSource } from "../../types/student";

/** Source badges (plan A6): where the information came from, and how far to trust it (C01, C24). */
export const SOURCE_BADGES: Record<ChatSource["trust"], string> = {
  instructor: "Instructor material",
  third_party: "Third-party source",
  blog_post: "Instructor blog post",
  student_comment: "Comment by a student",
};

/** Fixed system notices; never model-written. */
export const NOTICES: Record<NonNullable<ChatResponse["notice"]>, string> = {
  answer_key_blocked: "This answer was withheld because it might reveal part of an answer key. Ask your instructor if you need help.",
  agents_paused: "The course assistant is paused by your instructor. Try again later.",
};

type Turn = { from: "student"; text: string } | { from: "assistant"; response: ChatResponse };

/**
 * Student chat panel (A6; chat agent C6). Replies are model-written, so they
 * are rendered only through SafeMarkdown (C07): images become text, raw HTML is
 * dropped, off-site links aren't clickable. Each reply lists its sources.
 */
export function ChatPage() {
  const { courseId = "" } = useParams();
  const [params] = useSearchParams();
  const { api } = useAuth();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversation, setConversation] = useState<string | null>(null);
  const [message, setMessage] = useState(params.get("q") ?? "");
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  return (
    <section>
      <h1>Ask about the course</h1>
      <p className="muted">
        The assistant answers from course material and the blog. It can't see other students' work, and it never gives out
        answer keys.
      </p>
      <ol className="chat" aria-label="Conversation">
        {turns.map((t, i) =>
          t.from === "student" ? (
            <li key={i} className="chat-student">
              <span className="label-ai">You</span>
              <p className="prewrap">{t.text}</p>
            </li>
          ) : t.response.reply ? (
            <li key={i} className="chat-ai">
              <span className="label-ai">Answered by the AI assistant</span>
              <SafeMarkdown text={t.response.reply.text} />
              {t.response.reply.sources.length > 0 && (
                <ul className="badges" aria-label="Sources">
                  {t.response.reply.sources.map((s, j) => (
                    <li key={j} className={`badge source-${s.trust}`}>
                      {SOURCE_BADGES[s.trust]}: {s.label}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ) : (
            <li key={i} className="chat-notice" role="note">
              {t.response.notice ? NOTICES[t.response.notice] : "No answer."}
            </li>
          ),
        )}
      </ol>
      <form
        aria-label="Ask a question"
        onSubmit={(event) => {
          event.preventDefault();
          const text = message.trim();
          if (!text) return;
          setBusy(true);
          setError(null);
          setTurns((ts) => [...ts, { from: "student", text }]);
          setMessage("");
          studentRoutes(api)
            .chat(courseId, { message: text, conversation_id: conversation })
            .then((r) => {
              setConversation(r.conversation_id);
              setTurns((ts) => [...ts, { from: "assistant", response: r }]);
            })
            .catch((err: unknown) => setError(err))
            .finally(() => setBusy(false));
        }}
      >
        <label>
          Your question
          <textarea rows={3} maxLength={2000} value={message} onChange={(e) => setMessage(e.target.value)} />
        </label>
        {error !== null && <ErrorNotice error={error} />}
        <button type="submit" disabled={busy || !message.trim()}>
          Ask
        </button>
      </form>
    </section>
  );
}
