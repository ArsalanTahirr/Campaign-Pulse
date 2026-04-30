/**
 * Returns true if the event target is a text field where arrows / enter
 * should keep native behavior (avoid hijacking caret movement).
 */
export function isTextInputElement(target) {
  if (!target || typeof target !== "object") return false;
  const el = target;
  const tag = el.tagName?.toLowerCase();
  if (tag === "textarea") return true;
  if (tag !== "input") return false;
  const type = (el.type || "text").toLowerCase();
  return (
    type === "text" ||
    type === "search" ||
    type === "email" ||
    type === "password" ||
    type === "url" ||
    type === "tel" ||
    type === "number" ||
    type === ""
  );
}
