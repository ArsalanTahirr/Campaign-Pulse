"use client";

/**
 * SequenceBuilder — drag-free list of SequenceSteps with inline editing and
 * a slide-in StepEditorPanel for managing email variants.
 *
 * Props:
 *   workspaceId  {string}
 *   campaignId   {string}
 */

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Loader2, Mail, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import PermissionGate from "@/components/ui/PermissionGate";
import StepEditorPanel from "@/components/dashboard/StepEditorPanel";
import {
  DayPicker,
  DEFAULT_STEP_SEND_DAYS,
  normalizeSendTimeToHHMM,
} from "@/components/dashboard/stepScheduleShared";
import { messageFromApiErrorBody, userMessageFromFetchError } from "@/utils/apiError";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

function StepCard({ step, workspaceId, campaignId, onEdit, onDelete, deleting, readOnly }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
          {step.step_number}
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            Step {step.step_number}
            <span className="ml-2 text-xs font-normal text-slate-400">
              — wait {step.wait_days} {step.wait_days === 1 ? "day" : "days"} before sending
            </span>
          </p>
          <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
            {step.email_variants?.length || 0} variant{step.email_variants?.length !== 1 ? "s" : ""}
            {step.send_time ? ` · ${step.send_time}` : ""}
            {Array.isArray(step.send_days) && step.send_days.length > 0
              ? ` · ${step.send_days.map((d) => d.slice(0, 3)).join(", ")}`
              : ""}
          </p>
        </div>

        <div className="flex items-center gap-1">
          <PermissionGate action="manage_sequence">
            <button
              type="button"
              disabled={readOnly}
              onClick={() => onEdit(step)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-slate-700"
              aria-label="Edit step"
            >
              <Mail className="h-4 w-4" />
            </button>
            <button
              type="button"
              disabled={deleting || readOnly}
              onClick={() => onDelete(step.step_id)}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-500 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-slate-700"
              aria-label="Delete step"
            >
              {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            </button>
          </PermissionGate>
          <button
            type="button"
            onClick={() => setExpanded((p) => !p)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-slate-100 px-4 py-3 dark:border-slate-700">
          {step.email_variants?.length === 0 ? (
            <p className="text-xs text-amber-600">⚠ No email variants — add at least one before starting.</p>
          ) : (
            step.email_variants.map((v, i) => (
              <div key={v.email_id} className="mb-2 rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-700">
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                  Variant {i + 1} {v.from_name ? `(From: ${v.from_name})` : ""}
                </p>
                <p className="mt-0.5 truncate text-sm text-slate-700 dark:text-slate-200">{v.subject_line}</p>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function AddStepForm({ nextStepNumber, workspaceId, campaignId, onAdded, onCancel, readOnly }) {
  const [waitDays, setWaitDays] = useState(nextStepNumber === 1 ? 0 : 3);
  const [sendTime, setSendTime] = useState("09:00");
  const [sendDays, setSendDays] = useState([...DEFAULT_STEP_SEND_DAYS]);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const hhmm = normalizeSendTimeToHHMM(sendTime);
    if (!hhmm) {
      toast.error("Please set a send time for this step (24-hour clock, e.g. 09:00).");
      return;
    }
    if (!/^\d{2}:\d{2}$/.test(hhmm)) {
      toast.error("Send time must look like HH:MM (for example 09:30).");
      return;
    }
    if (sendDays.length === 0) {
      toast.error("Select at least one send day for this step.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/steps`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            step_number: nextStepNumber,
            wait_days: waitDays,
            send_time: hhmm,
            send_days: sendDays,
            email_variants: [],
          }),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to add step."));
      }
      const created = await res.json();
      toast.success(`Step ${created.step_number} added.`);
      onAdded(created);
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to add step."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-xl border-2 border-dashed border-blue-200 bg-blue-50/40 p-4 dark:border-blue-900 dark:bg-slate-800/50">
      <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">
        Step {nextStepNumber}
      </p>
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Wait days</label>
            <input
              type="number"
              min={0}
              disabled={readOnly}
              value={waitDays}
              onChange={(e) => setWaitDays(Number(e.target.value))}
              className="h-9 w-24 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">
              Send time <span className="text-rose-600">*</span> <span className="font-normal text-slate-400">(24h)</span>
            </label>
            <input
              type="time"
              required
              disabled={readOnly}
              value={sendTime}
              onChange={(e) => setSendTime(e.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400"
            />
          </div>
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-600 dark:text-slate-400">
            Send days <span className="text-rose-600">*</span>
          </label>
          <p className="mb-1.5 text-[11px] leading-snug text-slate-500 dark:text-slate-500">
            Sending days are set per step (Mon–Fri selected by default; change as needed).
          </p>
          <DayPicker value={sendDays} onChange={setSendDays} disabled={readOnly} />
        </div>
      </div>
      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          disabled={readOnly}
          onClick={onCancel}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting || readOnly}
          className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
          Add Step
        </button>
      </div>
    </form>
  );
}

export default function SequenceBuilder({ workspaceId, campaignId, campaignStatus }) {
  const readOnly = !["draft", "paused"].includes(campaignStatus);

  const [steps, setSteps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingStep, setEditingStep] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchSteps = useCallback(async () => {
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/steps`,
        { credentials: "include" }
      );
      if (res.ok) setSteps(await res.json());
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to load steps."));
    } finally {
      setLoading(false);
    }
  }, [workspaceId, campaignId]);

  useEffect(() => { fetchSteps(); }, [fetchSteps]);

  async function handleDelete(stepId) {
    setDeletingId(stepId);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/steps/${stepId}`,
        { method: "DELETE", credentials: "include" }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to delete step."));
      }
      setSteps((prev) => prev.filter((s) => s.step_id !== stepId));
      toast.success("Step removed.");
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to delete step."));
    } finally {
      setDeletingId(null);
    }
  }

  const nextStepNumber = (steps[steps.length - 1]?.step_number || 0) + 1;

  return (
    <div className="flex flex-1 overflow-hidden">
      <div className="flex flex-1 flex-col overflow-y-auto px-6 py-6">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
            Sequence Steps
          </h2>
          <PermissionGate action="manage_sequence">
            <button
              type="button"
              disabled={readOnly}
              onClick={() => setShowAddForm(true)}
              title={readOnly ? "Sequence edits are allowed only in draft or paused campaigns." : ""}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Plus className="h-4 w-4" />
              Add Step
            </button>
          </PermissionGate>
        </div>

        {readOnly && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-700">
            Sequence is read-only. Move campaign to Draft or Paused to edit steps and variants.
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {steps.map((step) => (
              <StepCard
                key={step.step_id}
                step={step}
                workspaceId={workspaceId}
                campaignId={campaignId}
                onEdit={(s) => setEditingStep(s)}
                onDelete={handleDelete}
                deleting={deletingId === step.step_id}
                readOnly={readOnly}
              />
            ))}

            {showAddForm && (
              <AddStepForm
                nextStepNumber={nextStepNumber}
                workspaceId={workspaceId}
                campaignId={campaignId}
                onAdded={(created) => {
                  setSteps((prev) => [...prev, created]);
                  setShowAddForm(false);
                  setEditingStep(created);
                }}
                onCancel={() => setShowAddForm(false)}
                readOnly={readOnly}
              />
            )}

            {steps.length === 0 && !showAddForm && (
              <div className="py-12 text-center">
                <p className="text-sm text-slate-500">No steps yet. Add your first step to get started.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {editingStep && (
        <div className="w-[420px] shrink-0 overflow-hidden">
          <StepEditorPanel
            step={steps.find((s) => s.step_id === editingStep.step_id) || editingStep}
            workspaceId={workspaceId}
            campaignId={campaignId}
            readOnly={readOnly}
            onClose={() => setEditingStep(null)}
            onSaved={fetchSteps}
          />
        </div>
      )}
    </div>
  );
}
