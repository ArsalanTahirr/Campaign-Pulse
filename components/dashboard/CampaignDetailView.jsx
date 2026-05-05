"use client";

/**
 * CampaignDetailView — the campaign detail page.
 *
 * Tabs:
 *  • Sequence  — SequenceBuilder (steps + email variants)
 *  • Leads     — lead list, bulk import
 *  • Runs      — execution history
 *
 * Top bar:
 *  • Campaign name + status badge
 *  • ExecutionControls (Start / Pause / Stop)
 *
 * Props:
 *   campaignId  {string}
 *   workspaceId {string}
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Check,
  ChevronDown,
  Download,
  Loader2,
  Mail,
  Pause,
  Play,
  Square,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import PermissionGate from "@/components/ui/PermissionGate";
import SequenceBuilder from "@/components/dashboard/SequenceBuilder";
import LeadImportModal from "@/components/dashboard/LeadImportModal";
import { messageFromApiErrorBody, userMessageFromFetchError } from "@/utils/apiError";
import {
  buildTimezoneOption,
  filterTimezoneOptions,
  getCampaignTimezoneOptions,
} from "@/utils/campaignTimezones";
import { isTextInputElement } from "@/utils/keyboard";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/** Headers only — matches common CRM exports; extra columns become merge fields. */
const LEAD_IMPORT_TEMPLATE_CSV =
  "email,first_name,last_name,company,title\n" +
  "jane.doe@example.com,Jane,Doe,Acme Inc.,VP Sales\n";

function downloadLeadImportTemplate() {
  const blob = new Blob([LEAD_IMPORT_TEMPLATE_CSV], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "campaign-pulse-leads-template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

const statusBadge = {
  draft:     "bg-slate-200 text-slate-700",
  active:    "bg-blue-600 text-white",
  paused:    "bg-amber-500 text-white",
  completed: "bg-emerald-600 text-white",
  error:     "bg-rose-500 text-white",
};

// ---------------------------------------------------------------------------
// Execution Controls
// ---------------------------------------------------------------------------

function ExecutionControls({ campaign, workspaceId, onTransitioned }) {
  const [loading, setLoading] = useState(null);

  const actions = {
    draft:     [{ label: "Start",  action: "started",  icon: Play,   cls: "bg-emerald-600 hover:bg-emerald-700 text-white" }],
    paused:    [
      { label: "Resume", action: "resumed", icon: Play,   cls: "bg-blue-600 hover:bg-blue-700 text-white" },
      { label: "Stop",   action: "stopped", icon: Square, cls: "bg-rose-500 hover:bg-rose-600 text-white" },
    ],
    active:    [
      { label: "Pause", action: "paused",  icon: Pause,  cls: "bg-amber-500 hover:bg-amber-600 text-white" },
      { label: "Stop",  action: "stopped", icon: Square, cls: "bg-rose-500 hover:bg-rose-600 text-white" },
    ],
    completed: [],
    error:     [],
  };

  const available = actions[campaign?.status] || [];
  if (!available.length) return null;

  async function fire(action) {
    setLoading(action);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaign.campaign_id}/runs`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action }),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, `Failed to ${action} campaign.`));
      }
      toast.success(`Campaign ${action}.`);
      onTransitioned?.();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setLoading(null);
    }
  }

  return (
    <PermissionGate action="start_campaign">
      <div className="flex items-center gap-2">
        {available.map(({ label, action, icon: Icon, cls }) => {
          const needsLeads =
            (action === "started" || action === "resumed") && (campaign.lead_count ?? 0) < 1;
          return (
            <button
              key={action}
              type="button"
              disabled={!!loading || needsLeads}
              title={
                needsLeads ? "Add at least one lead (Leads tab or import) before starting or resuming." : undefined
              }
              onClick={() => fire(action)}
              className={[
                "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold shadow-sm transition-all disabled:opacity-60",
                cls,
              ].join(" ")}
            >
              {loading === action ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
              {label}
            </button>
          );
        })}
      </div>
    </PermissionGate>
  );
}

// ---------------------------------------------------------------------------
// Lead Upload
// ---------------------------------------------------------------------------



// ---------------------------------------------------------------------------
// Leads Tab
// ---------------------------------------------------------------------------

/** Matches DB `lead_status` (outreach funnel) plus legacy engagement-style keys if ever used. */
const leadStatusBadge = {
  active:         "bg-blue-100 text-blue-800",
  replied:        "bg-emerald-100 text-emerald-800",
  unsubscribed:   "bg-amber-100 text-amber-800",
  bounced:        "bg-rose-100 text-rose-700",
  completed:      "bg-slate-200 text-slate-700",
  pending:        "bg-slate-200 text-slate-700",
  sent:           "bg-blue-100 text-blue-700",
  opened:         "bg-sky-100 text-sky-700",
  clicked:        "bg-violet-100 text-violet-700",
  opted_out:      "bg-amber-100 text-amber-700",
};

function LeadsTab({ workspaceId, campaignId, campaignStatus, onUploaded, onLeadDeleted }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [leadPendingRemove, setLeadPendingRemove] = useState(null);
  const [deletingLeadId, setDeletingLeadId] = useState(null);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/leads?limit=200`,
        { credentials: "include" }
      );
      if (res.ok) {
        const rows = await res.json();
        setLeads(rows);
      }
    } catch {
      toast.error("Failed to load leads.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, campaignId]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  useEffect(() => {
    if (!leadPendingRemove) return;
    function onKey(e) {
      if (e.key === "Escape") setLeadPendingRemove(null);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [leadPendingRemove]);

  const isLeadMutationLocked = ["completed", "deleted"].includes(campaignStatus);

  async function confirmRemoveLead() {
    if (!leadPendingRemove || deletingLeadId) return;
    const { lead_id, email } = leadPendingRemove;
    setDeletingLeadId(lead_id);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/leads/${lead_id}`,
        { method: "DELETE", credentials: "include" }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Could not remove lead."));
      }
      toast.success(`Removed ${email}`);
      setLeadPendingRemove(null);
      await fetchLeads();
      await onLeadDeleted?.();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDeletingLeadId(null);
    }
  }

  const handleUploaded = useCallback(async () => {
    await fetchLeads();
    await onUploaded?.();
  }, [fetchLeads, onUploaded]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="border-b border-slate-200 px-6 py-4 dark:border-slate-700">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-2">
            <p className="text-sm text-slate-500">
              {leads.length} lead{leads.length !== 1 ? "s" : ""}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={downloadLeadImportTemplate}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700/80"
            >
              <Download className="h-4 w-4" />
              Download Sample CSV
            </button>
            <PermissionGate action="import_leads">
              <button
                type="button"
                disabled={isLeadMutationLocked}
                onClick={() => setIsImportModalOpen(true)}
                title={isLeadMutationLocked ? "Completed/deleted campaigns are view-only for lead changes." : ""}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Upload className="h-4 w-4" />
                Import CSV/XLSX
              </button>
            </PermissionGate>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-sm text-slate-500">
              No leads yet. Download the sample CSV above for column names, then import your file.
            </p>
          </div>
        ) : (
          <table className="w-full table-fixed border-collapse text-sm">
            <colgroup>
              <col className="min-w-0" />
              <col style={{ width: "18%" }} />
              <col style={{ width: "7.25rem" }} />
              <col style={{ width: "10.75rem" }} />
              <col style={{ width: "3.25rem" }} />
            </colgroup>
            <thead className="sticky top-0 bg-white dark:bg-slate-900">
              <tr className="border-b border-slate-100 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:border-slate-800">
                <th className="min-w-0 px-6 py-3 text-left">Email</th>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="whitespace-nowrap px-3 py-3 text-left">Added</th>
                <th className="px-2 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.lead_id} className="border-b border-slate-50 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
                  <td className="min-w-0 truncate px-6 py-3 font-medium text-slate-700 dark:text-slate-200" title={lead.email}>
                    {lead.email}
                  </td>
                  <td className="min-w-0 truncate px-4 py-3 text-slate-600 dark:text-slate-400" title={[lead.first_name, lead.last_name].filter(Boolean).join(" ") || undefined}>
                    {[lead.first_name, lead.last_name].filter(Boolean).join(" ") || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={["rounded-full px-2.5 py-1 text-xs font-semibold", leadStatusBadge[lead.status] || "bg-slate-100 text-slate-600"].join(" ")}>
                      {lead.status}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-xs text-slate-500 dark:text-slate-400">
                    {lead.created_at
                      ? new Date(lead.created_at).toLocaleString(undefined, {
                          dateStyle: "short",
                          timeStyle: "short",
                        })
                      : "—"}
                  </td>
                  <td className="px-2 py-3 text-right">
                    <PermissionGate action="manage_leads">
                      <button
                        type="button"
                        disabled={isLeadMutationLocked || deletingLeadId === lead.lead_id}
                        title={
                          isLeadMutationLocked
                            ? "View-only campaign — leads cannot be changed."
                            : "Remove lead from this campaign"
                        }
                        aria-label={`Remove lead ${lead.email}`}
                        onClick={() =>
                          setLeadPendingRemove({
                            lead_id: lead.lead_id,
                            email: lead.email,
                            label: [lead.first_name, lead.last_name].filter(Boolean).join(" ") || lead.email,
                          })
                        }
                        className="inline-flex items-center justify-center rounded-lg border border-transparent p-2 text-slate-400 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:border-rose-900/50 dark:hover:bg-rose-950/40 dark:hover:text-rose-400"
                      >
                        {deletingLeadId === lead.lead_id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </button>
                    </PermissionGate>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {leadPendingRemove ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[1px]"
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setLeadPendingRemove(null);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="lead-remove-title"
            className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-600 dark:bg-slate-900"
            onMouseDown={(e) => e.stopPropagation()}
          >
            <h3 id="lead-remove-title" className="text-lg font-semibold text-slate-900 dark:text-slate-100">
              Remove lead?
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              <span className="font-medium text-slate-800 dark:text-slate-200">{leadPendingRemove.label}</span>
              {" "}
              <span className="text-slate-500">({leadPendingRemove.email})</span>
              {" "}
              will be removed from this campaign. Their mailbox is unchanged — only this campaign stops tracking them.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                disabled={!!deletingLeadId}
                onClick={() => setLeadPendingRemove(null)}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!!deletingLeadId}
                onClick={confirmRemoveLead}
                className="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-rose-700 disabled:opacity-60"
              >
                {deletingLeadId ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Remove lead
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <LeadImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        workspaceId={workspaceId}
        campaignId={campaignId}
        onUploaded={handleUploaded}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Runs Tab
// ---------------------------------------------------------------------------

function RunsTab({ workspaceId, campaignId }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch_() {
      try {
        const res = await fetch(
          `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/runs`,
          { credentials: "include" }
        );
        if (res.ok) setRuns(await res.json());
      } catch {
        toast.error("Failed to load run history.");
      } finally {
        setLoading(false);
      }
    }
    fetch_();
  }, [workspaceId, campaignId]);

  const runStatusBadge = {
    running:   "bg-blue-100 text-blue-700",
    paused:    "bg-amber-100 text-amber-700",
    completed: "bg-emerald-100 text-emerald-700",
    error:     "bg-rose-200 text-rose-700",
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      ) : runs.length === 0 ? (
        <p className="text-sm text-slate-500">No execution history yet.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {runs.map((run) => (
            <div key={run.run_id} className="rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={["rounded-full px-2.5 py-1 text-xs font-semibold capitalize", runStatusBadge[run.run_status] || "bg-slate-100 text-slate-600"].join(" ")}>
                    {run.run_status}
                  </span>
                  <span className="text-sm font-medium capitalize text-slate-700 dark:text-slate-200">{run.action}</span>
                </div>
                <span className="text-xs text-slate-400">{new Date(run.created_at).toLocaleString()}</span>
              </div>
              {run.error_message && (
                <p className="mt-2 rounded-lg bg-rose-50 px-3 py-2 text-xs text-rose-600">{run.error_message}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Campaign time zone
// ---------------------------------------------------------------------------

function CampaignTimezoneSettings({ workspaceId, campaignId, campaign, readOnly, onSaved }) {
  const [value, setValue] = useState(campaign.timezone || "UTC");
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [highlightIndex, setHighlightIndex] = useState(0);
  const [saving, setSaving] = useState(false);
  const rootRef = useRef(null);
  const searchInputRef = useRef(null);
  const optionRefs = useRef({});
  const highlightIndexRef = useRef(0);

  const allOptions = useMemo(() => getCampaignTimezoneOptions(), []);

  const selectedOption = useMemo(() => {
    const v = (value || "").trim();
    const found = allOptions.find((o) => o.value === v);
    if (found) return found;
    try {
      return buildTimezoneOption(v || "UTC");
    } catch {
      return { value: v || "UTC", label: v || "UTC" };
    }
  }, [allOptions, value]);

  const listOptions = useMemo(() => {
    let filtered = filterTimezoneOptions(allOptions, query);
    if (filtered.length === 0) filtered = allOptions;
    const v = (value || "").trim();
    if (v && !filtered.some((o) => o.value === v)) {
      try {
        return [buildTimezoneOption(v), ...filtered];
      } catch {
        return [{ value: v, label: v }, ...filtered];
      }
    }
    return filtered;
  }, [allOptions, query, value]);

  useEffect(() => {
    setValue(campaign.timezone || "UTC");
  }, [campaign.campaign_id, campaign.timezone]);

  useEffect(() => {
    highlightIndexRef.current = highlightIndex;
  }, [highlightIndex]);

  useEffect(() => {
    if (!open) return;
    if (query.trim() !== "") {
      setHighlightIndex(0);
      return;
    }
    const idx = listOptions.findIndex((o) => o.value === value);
    setHighlightIndex(idx >= 0 ? idx : 0);
  }, [open, query, listOptions, value]);

  useEffect(() => {
    if (!open) return;
    setHighlightIndex((i) =>
      listOptions.length === 0 ? 0 : Math.max(0, Math.min(i, listOptions.length - 1))
    );
  }, [listOptions.length, open]);

  useEffect(() => {
    if (!open || listOptions.length === 0) return;
    const el = optionRefs.current[highlightIndex];
    el?.scrollIntoView({ block: "nearest" });
  }, [highlightIndex, open, listOptions.length]);

  useEffect(() => {
    if (!open) return;
    function onDocMouseDown(e) {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false);
        setQuery("");
      }
    }
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [open]);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  useEffect(() => {
    if (!open || readOnly) return;

    function onKey(e) {
      const root = rootRef.current;
      if (!root?.contains(document.activeElement)) return;

      if (e.key === "Escape") {
        e.preventDefault();
        setOpen(false);
        setQuery("");
        return;
      }

      const max = Math.max(0, listOptions.length - 1);
      if (listOptions.length === 0) return;

      const active = document.activeElement;
      const inSearch = searchInputRef.current && active === searchInputRef.current;

      if (e.key === "ArrowDown") {
        if (inSearch && isTextInputElement(active)) {
          const pos = active.selectionStart ?? 0;
          const len = active.value?.length ?? 0;
          if (pos < len) return;
        }
        e.preventDefault();
        setHighlightIndex((i) => Math.min(i + 1, max));
        return;
      }
      if (e.key === "ArrowUp") {
        if (inSearch && isTextInputElement(active)) {
          const pos = active.selectionStart ?? 0;
          if (pos > 0) return;
        }
        e.preventDefault();
        setHighlightIndex((i) => Math.max(i - 1, 0));
        return;
      }
      if (e.key === "Home" && !inSearch) {
        e.preventDefault();
        setHighlightIndex(0);
        return;
      }
      if (e.key === "End" && !inSearch) {
        e.preventDefault();
        setHighlightIndex(max);
        return;
      }
      if (e.key === "Enter") {
        const o = listOptions[highlightIndexRef.current];
        if (o) {
          e.preventDefault();
          setValue(o.value);
          setOpen(false);
          setQuery("");
        }
      }
    }

    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, readOnly, listOptions]);

  async function save() {
    const trimmed = value.trim();
    if (!trimmed) {
      toast.error("Select a time zone.");
      return;
    }
    if (trimmed === (campaign.timezone || "UTC")) {
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}`,
        {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ timezone: trimmed }),
        }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(body, "Could not update time zone."));
      }
      toast.success("Time zone saved.");
      onSaved?.();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 border-b border-slate-200 bg-white px-6 py-5 dark:border-slate-700 dark:bg-slate-900 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
      <div ref={rootRef} className="min-w-0 flex-1 sm:max-w-xl">
        <label className="mb-2 block text-sm font-medium text-slate-800 dark:text-slate-100">
          Time zone
        </label>
        <div className="relative">
          <button
            type="button"
            id={`campaign-tz-trigger-${campaignId}`}
            disabled={readOnly}
            onClick={() => !readOnly && setOpen((o) => !o)}
            onKeyDown={(e) => {
              if (readOnly) return;
              if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                e.preventDefault();
                setOpen(true);
              }
            }}
            className="flex h-12 w-full items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-4 text-left text-base font-normal text-slate-900 shadow-sm outline-none transition hover:border-slate-300 focus-visible:ring-2 focus-visible:ring-blue-500/30 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:border-slate-500 dark:disabled:bg-slate-800/80"
            aria-haspopup="listbox"
            aria-expanded={open}
            aria-controls={open ? `campaign-tz-list-${campaignId}` : undefined}
          >
            <span className="min-w-0 truncate">{selectedOption.label}</span>
            <ChevronDown
              className={["h-4 w-4 shrink-0 text-slate-400 transition-transform", open ? "rotate-180" : ""].join(" ")}
              aria-hidden
            />
          </button>

          {open && !readOnly ? (
            <div
              id={`campaign-tz-list-${campaignId}`}
              className="absolute left-0 right-0 top-[calc(100%+4px)] z-50 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg ring-1 ring-black/5 dark:border-slate-600 dark:bg-slate-900 dark:ring-white/10"
            >
              <div className="border-b border-slate-100 p-2 dark:border-slate-700">
                <input
                  ref={searchInputRef}
                  autoFocus
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by city or region…"
                  autoComplete="off"
                  className="h-9 w-full rounded-md border border-slate-200 bg-slate-50 px-3 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-blue-400 focus:bg-white dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:focus:bg-slate-900"
                />
              </div>
              <ul role="listbox" aria-labelledby={`campaign-tz-trigger-${campaignId}`} className="max-h-60 overflow-y-auto py-1">
                {listOptions.map((o, i) => (
                  <li key={o.value} role="none">
                    <button
                      type="button"
                      role="option"
                      ref={(el) => {
                        optionRefs.current[i] = el;
                      }}
                      aria-selected={o.value === value}
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        setValue(o.value);
                        setOpen(false);
                        setQuery("");
                      }}
                      onMouseEnter={() => setHighlightIndex(i)}
                      className={[
                        "flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm outline-none",
                        i === highlightIndex
                          ? "bg-slate-100 ring-1 ring-inset ring-blue-400/50 dark:bg-slate-800"
                          : "",
                        o.value === value
                          ? "bg-blue-50 font-medium text-blue-900 dark:bg-blue-950/50 dark:text-blue-100"
                          : "text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800",
                      ].join(" ")}
                    >
                      {o.value === value ? (
                        <Check className="h-4 w-4 shrink-0 text-blue-600 dark:text-blue-400" strokeWidth={2.5} />
                      ) : (
                        <span className="h-4 w-4 shrink-0" aria-hidden />
                      )}
                      <span className="min-w-0 truncate">{o.label}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </div>
      <PermissionGate action="edit_campaign">
        <button
          type="button"
          disabled={readOnly || saving || !value.trim()}
          onClick={save}
          className="h-12 shrink-0 rounded-lg bg-slate-900 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </PermissionGate>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CampaignDetailView({ campaignId }) {
  const router = useRouter();
  const { workspace } = useWorkspace();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("sequence");
  const [deleting, setDeleting] = useState(false);
  const [senderPool, setSenderPool] = useState({ connected: [], available: [] });
  const [selectedSenderIds, setSelectedSenderIds] = useState([]);
  const [savingSenderPool, setSavingSenderPool] = useState(false);

  const workspaceId = workspace?.workspace_id;

  const fetchCampaign = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}`,
        { credentials: "include" }
      );
      if (res.ok) {
        const payload = await res.json().catch(() => null);
        if (payload) {
          setCampaign(payload);
        }
      }
    } catch {
      toast.error("Failed to load campaign.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, campaignId]);

  useEffect(() => { fetchCampaign(); }, [fetchCampaign]);

  const fetchSenderPool = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const res = await fetch(`${API}/workspaces/${workspaceId}/campaigns/${campaignId}/sender-pool`, {
        credentials: "include",
      });
      if (!res.ok) return;
      const data = await res.json();
      setSenderPool(data);
      setSelectedSenderIds((data.connected || []).map((s) => s.account_id));
    } catch {
      // non-fatal
    }
  }, [workspaceId, campaignId]);

  useEffect(() => {
    fetchSenderPool();
  }, [fetchSenderPool]);

  async function handleDeleteCampaign() {
    if (
      !window.confirm(
        `Delete “${campaign.name}”? It will be removed from this workspace.`
      )
    ) {
      return;
    }
    setDeleting(true);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}`,
        { method: "DELETE", credentials: "include" }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to delete campaign."));
      }
      toast.success(`Campaign “${campaign.name}” deleted.`);
      router.push("/dashboard/campaigns");
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to delete campaign."));
    } finally {
      setDeleting(false);
    }
  }

  async function saveSenderPool() {
    if (!workspaceId) return;
    setSavingSenderPool(true);
    try {
      const res = await fetch(`${API}/workspaces/${workspaceId}/campaigns/${campaignId}/sender-pool`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_ids: selectedSenderIds }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to update sender accounts."));
      }
      toast.success("Sender accounts updated.");
      await fetchCampaign();
      await fetchSenderPool();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to update sender accounts."));
    } finally {
      setSavingSenderPool(false);
    }
  }

  if (loading || !campaign) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-slate-50/60">
      {/* Header */}
      <div className="flex items-center gap-4 border-b border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
        <button
          type="button"
          onClick={() => router.push("/dashboard/campaigns")}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">{campaign.name}</h1>
          <p className="text-xs text-slate-400">
            {campaign.lead_count} leads · {campaign.step_count} steps
            {campaign.timezone ? (
              <span className="text-slate-500"> · {campaign.timezone}</span>
            ) : null}
          </p>
        </div>
        <span className={["rounded-full px-3 py-1 text-xs font-semibold capitalize", statusBadge[campaign.status] || "bg-slate-200 text-slate-700"].join(" ")}>
          {campaign.status}
        </span>
        <ExecutionControls
          campaign={campaign}
          workspaceId={workspaceId}
          onTransitioned={fetchCampaign}
        />
        {campaign.status !== "deleted" ? (
          <PermissionGate action="delete_campaign">
            <button
              type="button"
              disabled={deleting}
              onClick={handleDeleteCampaign}
              className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-600 shadow-sm transition hover:bg-rose-50 disabled:opacity-60 dark:border-rose-900/60 dark:bg-slate-900 dark:text-rose-400 dark:hover:bg-rose-950/40"
            >
              {deleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              Delete
            </button>
          </PermissionGate>
        ) : null}
      </div>
      {["completed", "deleted"].includes(campaign.status) && (
        <div className="border-b border-amber-200 bg-amber-50 px-6 py-2 text-xs font-medium text-amber-700">
          This campaign is view-only. Lead and sequence mutations are disabled.
        </div>
      )}

      <CampaignTimezoneSettings
        workspaceId={workspaceId}
        campaignId={campaignId}
        campaign={campaign}
        readOnly={["completed", "deleted"].includes(campaign.status)}
        onSaved={fetchCampaign}
      />

      <div className="border-b border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-slate-100 p-2 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            <Mail className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Sender accounts</h2>
            {(campaign.sender_accounts || []).length === 0 ? (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                No sender accounts are assigned yet. Add one from the campaign sender pool before starting.
              </p>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                {campaign.sender_accounts.map((sender) => (
                  <span
                    key={sender.account_id}
                    className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  >
                    {sender.email}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="border-b border-slate-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Campaign sender pool</h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Select which workspace accounts are connected to this campaign for sending rotation.
            </p>
          </div>
          <PermissionGate action="edit_campaign">
            <button
              type="button"
              onClick={saveSenderPool}
              disabled={savingSenderPool}
              className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-60 dark:bg-slate-100 dark:text-slate-900"
            >
              {savingSenderPool ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Save pool
            </button>
          </PermissionGate>
        </div>
        <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {(senderPool.available || []).map((sender) => {
            const checked = selectedSenderIds.includes(sender.account_id);
            return (
              <label
                key={sender.account_id}
                className={[
                  "flex items-center justify-between rounded-lg border px-3 py-2 text-sm",
                  checked
                    ? "border-blue-300 bg-blue-50 text-blue-900 dark:border-blue-800 dark:bg-blue-950/40 dark:text-blue-100"
                    : "border-slate-200 bg-white text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
                ].join(" ")}
              >
                <span className="truncate pr-2">{sender.email}</span>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedSenderIds((prev) => [...prev, sender.account_id]);
                    } else {
                      setSelectedSenderIds((prev) => prev.filter((id) => id !== sender.account_id));
                    }
                  }}
                  className="h-4 w-4"
                />
              </label>
            );
          })}
          {(senderPool.available || []).length === 0 ? (
            <p className="text-xs text-slate-500 dark:text-slate-400">No active sender accounts in workspace.</p>
          ) : null}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 bg-white px-6 dark:border-slate-700 dark:bg-slate-900">
        {["sequence", "leads", "runs"].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={[
              "border-b-2 px-4 py-3 text-sm font-semibold capitalize transition-colors",
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700",
            ].join(" ")}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex flex-1 overflow-hidden">
        {tab === "sequence" && workspaceId && (
          <SequenceBuilder workspaceId={workspaceId} campaignId={campaignId} campaignStatus={campaign.status} />
        )}
        {tab === "leads" && workspaceId && (
          <LeadsTab
            workspaceId={workspaceId}
            campaignId={campaignId}
            campaignStatus={campaign.status}
            onUploaded={fetchCampaign}
            onLeadDeleted={fetchCampaign}
          />
        )}
        {tab === "runs" && workspaceId && (
          <RunsTab workspaceId={workspaceId} campaignId={campaignId} />
        )}
      </div>
    </div>
  );
}
