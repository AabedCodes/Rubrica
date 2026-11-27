import { useCallback, useState } from "react";
import { useParams } from "react-router";
import { useAuth } from "../../auth/AuthContext";
import { ErrorNotice } from "../../components/ErrorNotice";
import { SafeMarkdown } from "../../components/SafeMarkdown";
import { studentRoutes } from "../../endpoints";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../rubric";
import type { Author } from "../../types/student";

/** Who wrote it, in words (plan A6): student comments are visibly marked as such (TB-5). */
export function authorLabel(a: Author, kind: "post" | "comment"): string {
  if (kind === "post") return "Instructor blog post";
  return a.role === "student" ? "Comment by a student" : "Comment by the instructor";
}

/**
 * Course blog (A6, D7). Blog text is untrusted: it is rendered only through
 * SafeMarkdown, and students' comments are labelled as written by students.
 */
export function BlogPage() {
  const { courseId = "" } = useParams();
  const { api, state: auth } = useAuth();
  const instructor = auth.status === "signed_in" && auth.me.role === "instructor";
  const loader = useCallback(() => studentRoutes(api).blogPosts(courseId), [api, courseId]);
  const { state, reload } = useLoad(loader);
  const [newPost, setNewPost] = useState("");
  const [error, setError] = useState<unknown>(null);

  const act = (p: Promise<unknown>) => {
    setError(null);
    p.then(() => reload()).catch((err: unknown) => setError(err));
  };

  return (
    <section>
      <h1>Course blog</h1>
      {error !== null && <ErrorNotice error={error} />}
      {instructor && (
        <form
          aria-label="New post"
          onSubmit={(event) => {
            event.preventDefault();
            if (!newPost.trim()) return;
            act(studentRoutes(api).createPost(courseId, newPost.trim()).then(() => setNewPost("")));
          }}
        >
          <label>
            New post (Markdown)
            <textarea rows={3} value={newPost} onChange={(e) => setNewPost(e.target.value)} />
          </label>
          <button type="submit" disabled={!newPost.trim()}>
            Publish post
          </button>
        </form>
      )}
      {state.status === "loading" && <p className="muted">Loading…</p>}
      {state.status === "error" && <ErrorNotice error={state.error} />}
      {state.status === "ok" && state.data.length === 0 && <p>No posts yet.</p>}
      {state.status === "ok" &&
        state.data.map((post) => (
          <article key={post.id} className="card" aria-label={`Post by ${post.author.display_name}`}>
            <span className="badge source-blog_post">{authorLabel(post.author, "post")}</span>{" "}
            <span className="muted">
              {post.author.display_name}, {formatDate(post.created_at)}
            </span>
            <SafeMarkdown text={post.body} />
            {instructor && (
              <button type="button" onClick={() => act(studentRoutes(api).deletePost(post.id))}>
                Delete post
              </button>
            )}
            <ul className="comments">
              {post.comments.map((c) => (
                <li key={c.id} aria-label={`Comment by ${c.author.display_name}`}>
                  <span className={`badge ${c.author.role === "student" ? "source-student_comment" : "source-blog_post"}`}>
                    {authorLabel(c.author, "comment")}
                  </span>{" "}
                  <span className="muted">
                    {c.author.display_name}, {formatDate(c.created_at)}
                  </span>
                  <SafeMarkdown text={c.body} />
                  {instructor && (
                    <button type="button" onClick={() => act(studentRoutes(api).deleteComment(c.id))}>
                      Delete comment
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <CommentForm onSubmit={(body) => act(studentRoutes(api).comment(post.id, body))} />
          </article>
        ))}
    </section>
  );
}

function CommentForm({ onSubmit }: { onSubmit: (body: string) => void }) {
  const [body, setBody] = useState("");
  return (
    <form
      aria-label="Add a comment"
      onSubmit={(event) => {
        event.preventDefault();
        if (!body.trim()) return;
        onSubmit(body.trim());
        setBody("");
      }}
    >
      <label>
        Your comment
        <textarea rows={2} maxLength={2000} value={body} onChange={(e) => setBody(e.target.value)} />
      </label>
      <button type="submit" disabled={!body.trim()}>
        Comment
      </button>
    </form>
  );
}
