"use client";

import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

function utcMonthLength(year, month0) {
  return new Date(Date.UTC(year, month0 + 1, 0)).getUTCDate();
}

function utcFirstWeekday(year, month0) {
  return new Date(Date.UTC(year, month0, 1)).getUTCDay();
}

function ymdUtc(y, m0, d) {
  const s = `${y}-${String(m0 + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  return s;
}

function parseYmd(s) {
  if (!s || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const [y, m, d] = s.split("-").map(Number);
  return { y, m0: m - 1, d };
}

function monthLabel(year, month0) {
  return new Date(Date.UTC(year, month0, 1)).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * Modal calendar (UTC dates) for picking an inclusive custom range. Matches
 * common analytics “start → end” flow with Clear + Apply.
 */
export default function AnalyticsDateRangeCalendar({
  open,
  onClose,
  initialFrom,
  initialTo,
  onApply,
}) {
  const initial = useMemo(() => {
    const a = parseYmd(initialFrom);
    const now = new Date();
    const y = a?.y ?? now.getUTCFullYear();
    const m = a?.m0 ?? now.getUTCMonth();
    return { viewY: y, viewM: m, anchor: initialFrom || null, focus: initialTo || null };
  }, [initialFrom, initialTo]);

  const [viewY, setViewY] = useState(initial.viewY);
  const [viewM, setViewM] = useState(initial.viewM);
  const [anchor, setAnchor] = useState(initial.anchor);
  const [focus, setFocus] = useState(initial.focus);

  useEffect(() => {
    if (!open) return;
    setViewY(initial.viewY);
    setViewM(initial.viewM);
    setAnchor(initial.anchor);
    setFocus(initial.focus);
  }, [open, initial]);

  if (!open) return null;

  const len = utcMonthLength(viewY, viewM);
  const pad = utcFirstWeekday(viewY, viewM);
  const cells = [];
  for (let i = 0; i < pad; i += 1) cells.push(null);
  for (let d = 1; d <= len; d += 1) cells.push(d);

  function inRange(d) {
    if (!anchor || !d) return false;
    const cur = ymdUtc(viewY, viewM, d);
    if (!focus) return cur === anchor;
    const lo = anchor < focus ? anchor : focus;
    const hi = anchor < focus ? focus : anchor;
    return cur >= lo && cur <= hi;
  }

  function isEndpoint(d) {
    if (!d) return false;
    const cur = ymdUtc(viewY, viewM, d);
    return cur === anchor || cur === focus;
  }

  function onDayClick(d) {
    const cur = ymdUtc(viewY, viewM, d);
    if (!anchor || (anchor && focus)) {
      setAnchor(cur);
      setFocus(null);
      return;
    }
    if (cur < anchor) {
      setFocus(anchor);
      setAnchor(cur);
    } else {
      setFocus(cur);
    }
  }

  function shiftMonth(delta) {
    let m = viewM + delta;
    let y = viewY;
    while (m < 0) {
      m += 12;
      y -= 1;
    }
    while (m > 11) {
      m -= 12;
      y += 1;
    }
    setViewM(m);
    setViewY(y);
  }

  const labelLo = anchor && focus && anchor <= focus ? anchor : anchor && focus ? focus : anchor;
  const labelHi = anchor && focus && anchor <= focus ? focus : anchor && focus ? anchor : focus;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/40 p-4"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Custom date range"
        className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-4 shadow-2xl dark:border-slate-700 dark:bg-slate-900"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <p className="text-base font-semibold text-slate-900 dark:text-slate-100">
            {monthLabel(viewY, viewM)}
          </p>
          <div className="flex gap-1">
            <button
              type="button"
              aria-label="Previous month"
              className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              onClick={() => shiftMonth(-1)}
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <button
              type="button"
              aria-label="Next month"
              className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              onClick={() => shiftMonth(1)}
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-7 gap-y-1 text-center text-xs font-semibold uppercase text-slate-700 dark:text-slate-300">
          {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((d) => (
            <span key={d}>{d}</span>
          ))}
        </div>

        <div className="mt-1 grid grid-cols-7 gap-y-0.5 text-center text-sm">
          {cells.map((d, i) =>
            d == null ? (
              <span key={`e-${i}`} className="h-9" />
            ) : (
              <button
                key={`d-${d}`}
                type="button"
                onClick={() => onDayClick(d)}
                className={[
                  "mx-auto flex h-9 w-9 items-center justify-center rounded-full text-slate-800 transition-colors dark:text-slate-100",
                  inRange(d) ? "bg-sky-100 dark:bg-sky-900/50" : "hover:bg-slate-100 dark:hover:bg-slate-800",
                  isEndpoint(d) ? "font-bold ring-2 ring-blue-600 dark:ring-blue-400" : "",
                ].join(" ")}
              >
                {d}
              </button>
            )
          )}
        </div>

        <div className="mt-4 border-t border-slate-200 pt-3 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          {labelLo && labelHi ? (
            <span className="text-slate-800 dark:text-slate-200">
              {labelLo} <span className="text-slate-400">to</span> {labelHi}
            </span>
          ) : (
            <span className="text-slate-400">to</span>
          )}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
            onClick={() => {
              setAnchor(null);
              setFocus(null);
            }}
          >
            Clear
          </button>
          <button
            type="button"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-40"
            disabled={!anchor || !focus}
            onClick={() => {
              const lo = anchor < focus ? anchor : focus;
              const hi = anchor < focus ? focus : anchor;
              onApply({ from: lo, to: hi });
              onClose();
            }}
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}
