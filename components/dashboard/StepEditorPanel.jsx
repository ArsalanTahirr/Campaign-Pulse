"use client";

/**
 * StepEditorPanel — slide-in panel for editing a single SequenceStep's email
 * variants.  Shown when the user clicks "Edit" on a step in SequenceBuilder.
 *
 * Props:
 *   step         {object}   — the step being edited
 *   workspaceId  {string}
 *   campaignId   {string}
 *   onClose      {function} — called when the panel is dismissed
 *   onSaved      {function} — called after any save so the parent can refetch
 */

import { useEffect, useState } from "react";
import { Loader2, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import {
  DayPicker,
  DEFAULT_STEP_SEND_DAYS,
  hhmmToMinutes,
  normalizeSendTimeToHHMM,
} from "@/components/dashboard/stepScheduleShared";
import { messageFromApiErrorBody, userMessageFromFetchError } from "@/utils/apiError";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function VariantForm({ variant, onSave, onDelete, saving, deleting, readOnly = false }) {
  const [subject, setSubject] = useState(variant?.subject_line || "");
  const [body, setBody] = useState(variant?.email_body || "");
  const [fromName, setFromName] = useState(variant?.from_name || "");
  const isNew = !variant?.email_id;

  function handleSubmit(event) {
    event.preventDefault();
    onSave({ subject_line: subject.trim(), email_body: body.trim(), from_name: fromName.trim() || null });
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {isNew ? "New variant" : "Variant"}
        </span>
        {!isNew && (
          <button
            type="button"
            onClick={onDelete}
            disabled={deleting || readOnly}
            className="rounded-lg p-1 text-slate-400 hover:bg-rose-50 hover:text-rose-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        )}
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Subject line</label>
          <input
            type="text"
            disabled={readOnly}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Quick question, {{first_name}}"
            className="h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
            required
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">From name (optional)</label>
          <input
            type="text"
            disabled={readOnly}
            value={fromName}
            onChange={(e) => setFromName(e.target.value)}
            placeholder="e.g. Sarah from Acme"
            className="h-9 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Email body</label>
          <textarea
            value={body}
            disabled={readOnly}
            onChange={(e) => setBody(e.target.value)}
            rows={7}
            placeholder={"Hi {{first_name}},\n\nI wanted to reach out…"}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 font-mono text-sm text-slate-700 outline-none transition-colors focus:border-blue-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
            required
          />
        </div>

        <button
          type="submit"
          disabled={saving || readOnly || !subject.trim() || !body.trim()}
          className="inline-flex items-center gap-2 self-end rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {isNew ? "Add Variant" : "Save"}
        </button>
      </div>
    </form>
  );
}

export default function StepEditorPanel({ step, workspaceId, campaignId, readOnly = false, onClose, onSaved }) {
  const [variants, setVariants] = useState(step?.email_variants || []);
  const [showNewForm, setShowNewForm] = useState(variants.length === 0);
  const [savingId, setSavingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const [waitDays, setWaitDays] = useState(step?.wait_days ?? 0);
  const [sendTime, setSendTime] = useState(normalizeSendTimeToHHMM(step?.send_time || "09:00"));
  const [sendWindowEnd, setSendWindowEnd] = useState(
    normalizeSendTimeToHHMM(step?.send_window_end || "17:00")
  );
  const [sendDays, setSendDays] = useState(() => {
    const sd = step?.send_days;
    if (Array.isArray(sd) && sd.length > 0) return [...sd];
    return [...DEFAULT_STEP_SEND_DAYS];
  });
  const [savingSchedule, setSavingSchedule] = useState(false);

  useEffect(() => {
    setVariants(step?.email_variants || []);
    setShowNewForm((step?.email_variants || []).length === 0);
  }, [step]);

  useEffect(() => {
    setWaitDays(step?.wait_days ?? 0);
    setSendTime(normalizeSendTimeToHHMM(step?.send_time || "09:00"));
    setSendWindowEnd(normalizeSendTimeToHHMM(step?.send_window_end || "17:00"));
    const sd = step?.send_days;
    setSendDays(
      Array.isArray(sd) && sd.length > 0 ? [...sd] : [...DEFAULT_STEP_SEND_DAYS]
    );
  }, [step?.step_id, step?.wait_days, step?.send_time, step?.send_window_end, step?.send_days]);

  const base = `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/steps/${step?.step_id}/emails`;
  const stepBase = `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/steps/${step?.step_id}`;

  async function handleSaveSchedule(event) {
    event?.preventDefault();
    const hhmm = normalizeSendTimeToHHMM(sendTime);
    const endHHMM = normalizeSendTimeToHHMM(sendWindowEnd);
    if (!hhmm) {
      toast.error("Please set a start time (24-hour clock, e.g. 09:00).");
      return;
    }
    if (!endHHMM) {
      toast.error("Please set an end time (e.g. 17:00).");
      return;
    }
    if (!/^\d{2}:\d{2}$/.test(hhmm) || !/^\d{2}:\d{2}$/.test(endHHMM)) {
      toast.error("Times must look like HH:MM (for example 09:30).");
      return;
    }
    if (hhmmToMinutes(endHHMM) < hhmmToMinutes(hhmm)) {
      toast.error("End time must be the same as or after start time.");
      return;
    }
    if (sendDays.length === 0) {
      toast.error("Select at least one send day for this step.");
      return;
    }
    setSavingSchedule(true);
    try {
      const res = await fetch(stepBase, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          wait_days: waitDays,
          send_time: hhmm,
          send_window_end: endHHMM,
          send_days: sendDays,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to save schedule."));
      }
      toast.success("Schedule saved.");
      onSaved?.();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to save schedule."));
    } finally {
      setSavingSchedule(false);
    }
  }

  async function handleSaveNew(data) {
    setSavingId("new");
    try {
      const res = await fetch(base, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to add variant."));
      }
      const created = await res.json();
      setVariants((prev) => [...prev, created]);
      setShowNewForm(false);
      toast.success("Variant added.");
      onSaved?.();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to add variant."));
    } finally {
      setSavingId(null);
    }
  }

  async function handleSaveExisting(emailId, data) {
    setSavingId(emailId);
    try {
      const res = await fetch(`${base}/${emailId}`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to save variant."));
      }
      const updated = await res.json();
      setVariants((prev) => prev.map((v) => (v.email_id === emailId ? updated : v)));
      toast.success("Variant saved.");
      onSaved?.();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to save variant."));
    } finally {
      setSavingId(null);
    }
  }

  async function handleDelete(emailId) {
    setDeletingId(emailId);
    try {
      const res = await fetch(`${base}/${emailId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to delete variant."));
      }
      setVariants((prev) => prev.filter((v) => v.email_id !== emailId));
      toast.success("Variant removed.");
      onSaved?.();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to delete variant."));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden border-l border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-4 dark:border-slate-700 dark:bg-slate-800">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Step {step?.step_number}</p>
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">Email Variants</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        <form
          onSubmit={handleSaveSchedule}
          className="mb-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800"
        >
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
            Schedule
          </h3>
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">Wait days</label>
                <input
                  type="number"
                  min={0}
                  disabled={readOnly}
                  value={waitDays}
                  onChange={(e) => setWaitDays(Number(e.target.value))}
                  className="h-9 w-24 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">
                  Start time <span className="text-rose-600">*</span>
                </label>
                <input
                  type="time"
                  required
                  disabled={readOnly}
                  value={sendTime}
                  onChange={(e) => setSendTime(e.target.value)}
                  className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-slate-600 dark:text-slate-400">
                  End time <span className="text-rose-600">*</span>
                </label>
                <input
                  type="time"
                  required
                  disabled={readOnly}
                  value={sendWindowEnd}
                  onChange={(e) => setSendWindowEnd(e.target.value)}
                  className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
                />
              </div>
            </div>
            <p className="text-[11px] leading-snug text-slate-500 dark:text-slate-500">
              Same start and end time means one send slot (that minute), not all day. For a full-day window, use{" "}
              <span className="font-mono">00:00</span> and <span className="font-mono">23:59</span> in the campaign
              timezone.
            </p>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-400">
                Send days <span className="text-rose-600">*</span>
              </label>
              <p className="mb-1.5 text-[11px] leading-snug text-slate-500 dark:text-slate-500">
                Emails send only on these weekdays, between start and end time (inclusive), in the campaign&apos;s timezone.
              </p>
              <DayPicker value={sendDays} onChange={setSendDays} disabled={readOnly} />
            </div>
          </div>
          <button
            type="submit"
            disabled={readOnly || savingSchedule}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            {savingSchedule && <Loader2 className="h-4 w-4 animate-spin" />}
            Save schedule
          </button>
        </form>

        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
          Add multiple variants — the sending engine rotates through them across your mailboxes.
          Use <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px] dark:bg-slate-700">{"{{first_name}}"}</code> for merge tags.
        </p>
        {readOnly && (
          <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
            Variants are read-only for active/completed campaigns. Pause or draft the campaign to edit.
          </p>
        )}

        {variants.map((variant) => (
          <VariantForm
            key={variant.email_id}
            variant={variant}
            onSave={(data) => handleSaveExisting(variant.email_id, data)}
            onDelete={() => handleDelete(variant.email_id)}
            saving={savingId === variant.email_id}
            deleting={deletingId === variant.email_id}
            readOnly={readOnly}
          />
        ))}

        {showNewForm ? (
          <VariantForm
            variant={null}
            onSave={handleSaveNew}
            onDelete={() => setShowNewForm(false)}
            saving={savingId === "new"}
            deleting={false}
            readOnly={readOnly}
          />
        ) : (
          <button
            type="button"
            disabled={readOnly}
            onClick={() => setShowNewForm(true)}
            className="flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed border-slate-200 py-3 text-sm font-medium text-slate-400 transition-colors hover:border-blue-300 hover:text-blue-500 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:hover:border-blue-600"
          >
            <Plus className="h-4 w-4" />
            Add Variant
          </button>
        )}
      </div>
    </div>
  );
}
