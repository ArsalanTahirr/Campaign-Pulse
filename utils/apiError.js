/**
 * Turns FastAPI / Pydantic error bodies into a single user-visible string.
 * Avoids "[object Object]" when `detail` is an array of validation errors.
 */
export function messageFromApiErrorBody(body, fallback = "Something went wrong.") {
  const detail = body?.detail;
  if (detail == null || detail === "") return fallback;
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const parts = detail.map((item) => formatValidationItem(item)).filter(Boolean);
    return parts.length ? parts.join(" ") : fallback;
  }

  if (typeof detail === "object" && detail !== null) {
    if (typeof detail.msg === "string") return detail.msg;
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }

  return fallback;
}

/**
 * Browser `fetch` throws TypeError with message "Failed to fetch" for CORS, DNS, or offline.
 */
export function userMessageFromFetchError(err, fallback = "Request failed.") {
  const name = err?.name;
  const msg = typeof err?.message === "string" ? err.message : "";
  if (name === "AbortError") {
    return (
      "The request took too long and was cancelled. " +
      "IMAP scans can be slow with many accounts; check the API terminal for errors or try again."
    );
  }
  if (
    name === "TypeError" ||
    msg === "Failed to fetch" ||
    msg.includes("NetworkError when attempting to fetch")
  ) {
    return (
      "Could not reach the API. Is the backend running on port 8000? " +
      "If the site is open at 127.0.0.1, try localhost (or the reverse) so it matches FRONTEND_URL in .env."
    );
  }
  return msg || fallback;
}

const FIELD_LABELS = {
  send_time: "Send time",
  send_window_end: "Send window end",
  wait_days: "Wait days",
  step_number: "Step number",
  subject_line: "Subject line",
  email_body: "Email body",
  name: "Name",
  timezone: "Timezone",
  send_days: "Send days",
};

function humanizeField(field) {
  if (FIELD_LABELS[field]) return FIELD_LABELS[field];
  return String(field).replace(/_/g, " ");
}

function formatValidationItem(item) {
  if (typeof item === "string") return item;
  if (!item || typeof item !== "object") return "";

  const loc = Array.isArray(item.loc) ? item.loc : [];
  const rawField = loc.length ? loc[loc.length - 1] : null;
  const fieldLabel = rawField != null ? humanizeField(rawField) : "Field";
  const msg = typeof item.msg === "string" ? item.msg : "Invalid value";

  // e.g. "Send time: Field required"
  return `${fieldLabel}: ${msg}.`;
}
