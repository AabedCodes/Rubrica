import { ApiError } from "../api";

/** Plain-language text for an API error. Never shows server-provided text. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.code) {
      case "not_found":
        return "Not found, or you don't have access to it.";
      case "forbidden":
        return "Your role can't do this.";
      case "invalid_request":
        return "The server rejected this request. Check the form and try again.";
      case "deadline_passed":
        return "The due date has passed, so submissions are closed.";
      case "reauth_required":
        return "This action needs your authenticator code. Try again and confirm when asked.";
      case "rate_limited":
        return "Too many requests. Wait a minute and try again.";
      case "unauthenticated":
        return "Your session ended. Sign in again.";
      default:
        break;
    }
  }
  return "Something went wrong. Try again.";
}

export function ErrorNotice({ error }: { error: unknown }) {
  return (
    <p className="error" role="alert">
      {errorMessage(error)}
    </p>
  );
}
