"use client";

/** Shared wait / send time / send days controls for sequence steps. */

/** HTML time input may return HH:MM or HH:MM:SS — API expects HH:MM */
export function normalizeSendTimeToHHMM(value) {
  if (!value || typeof value !== "string") return "";
  const v = value.trim();
  if (v.length >= 5 && v[2] === ":") return v.slice(0, 5);
  return v;
}

export const SCHEDULE_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

/** Default when adding a step — user can change before save. */
export const DEFAULT_STEP_SEND_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

export function DayPicker({ value, onChange, disabled = false }) {
  const selected = value || [];
  function toggle(day) {
    onChange(selected.includes(day) ? selected.filter((d) => d !== day) : [...selected, day]);
  }
  return (
    <div className="flex flex-wrap gap-1">
      {SCHEDULE_DAYS.map((d) => (
        <button
          key={d}
          type="button"
          disabled={disabled}
          onClick={() => toggle(d)}
          className={[
            "rounded-full px-2.5 py-1 text-xs font-semibold transition-colors",
            selected.includes(d)
              ? "bg-blue-600 text-white"
              : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600",
            disabled ? "cursor-not-allowed opacity-50 hover:bg-slate-100 dark:hover:bg-slate-700" : "",
          ].join(" ")}
        >
          {d.slice(0, 3)}
        </button>
      ))}
    </div>
  );
}
