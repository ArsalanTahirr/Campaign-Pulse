"use client";

/**
 * CampaignDetailView — the campaign detail page.
 *
 * Tabs:
 *  • Sequence  — SequenceBuilder (steps + email variants)
 *  • Leads     — lead list, bulk import, CSV export
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

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Download,
  Loader2,
  Pause,
  Play,
  Square,
  Upload,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import PermissionGate from "@/components/ui/PermissionGate";
import SequenceBuilder from "@/components/dashboard/SequenceBuilder";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

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
        throw new Error(err.detail || `Failed to ${action} campaign.`);
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
        {available.map(({ label, action, icon: Icon, cls }) => (
          <button
            key={action}
            type="button"
            disabled={!!loading}
            onClick={() => fire(action)}
            className={[
              "inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold shadow-sm transition-all disabled:opacity-60",
              cls,
            ].join(" ")}
          >
            {loading === action ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
            {label}
          </button>
        ))}
      </div>
    </PermissionGate>
  );
}

// ---------------------------------------------------------------------------
// Lead Upload
// ---------------------------------------------------------------------------

function LeadUploadButton({ workspaceId, campaignId, onUploaded }) {
  const inputRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/leads/import`,
        { method: "POST", credentials: "include", body: form }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Upload failed.");
      }
      const session = await res.json();
      toast.success(
        `Imported ${session.imported_count} leads (${session.skipped_count} skipped, ${session.error_count} errors).`
      );
      onUploaded?.();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <PermissionGate action="import_leads">
      <>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx"
          className="hidden"
          onChange={handleFile}
        />
        <button
          type="button"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-60"
        >
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          Import CSV/XLSX
        </button>
      </>
    </PermissionGate>
  );
}

// ---------------------------------------------------------------------------
// Export Button
// ---------------------------------------------------------------------------

function ExportButton({ workspaceId, campaignId }) {
  const [downloading, setDownloading] = useState(false);

  async function handleExport() {
    setDownloading(true);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/leads/export`,
        { credentials: "include" }
      );
      if (!res.ok) throw new Error("Export failed.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `leads_${campaignId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDownloading(false);
    }
  }

  return (
    <PermissionGate action="export_leads">
      <button
        type="button"
        disabled={downloading}
        onClick={handleExport}
        className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-60"
      >
        {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
        Export CSV
      </button>
    </PermissionGate>
  );
}

// ---------------------------------------------------------------------------
// Leads Tab
// ---------------------------------------------------------------------------

const leadStatusBadge = {
  pending:   "bg-slate-200 text-slate-700",
  sent:      "bg-blue-100 text-blue-700",
  opened:    "bg-sky-100 text-sky-700",
  clicked:   "bg-violet-100 text-violet-700",
  replied:   "bg-emerald-100 text-emerald-700",
  bounced:   "bg-rose-100 text-rose-600",
  opted_out: "bg-amber-100 text-amber-700",
};

function LeadsTab({ workspaceId, campaignId }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}/leads?limit=200`,
        { credentials: "include" }
      );
      if (res.ok) setLeads(await res.json());
    } catch {
      toast.error("Failed to load leads.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, campaignId]);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
        <p className="text-sm text-slate-500">{leads.length} lead{leads.length !== 1 ? "s" : ""}</p>
        <div className="flex items-center gap-2">
          <LeadUploadButton workspaceId={workspaceId} campaignId={campaignId} onUploaded={fetchLeads} />
          <ExportButton workspaceId={workspaceId} campaignId={campaignId} />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-sm text-slate-500">No leads yet. Import a CSV to get started.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-white dark:bg-slate-900">
              <tr className="border-b border-slate-100 text-[11px] font-semibold uppercase tracking-wide text-slate-400 dark:border-slate-800">
                <th className="px-6 py-3 text-left">Email</th>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Added</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.lead_id} className="border-b border-slate-50 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50">
                  <td className="px-6 py-3 font-medium text-slate-700 dark:text-slate-200">{lead.email}</td>
                  <td className="px-4 py-3 text-slate-600 dark:text-slate-400">
                    {[lead.first_name, lead.last_name].filter(Boolean).join(" ") || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={["rounded-full px-2.5 py-1 text-xs font-semibold", leadStatusBadge[lead.status] || "bg-slate-100 text-slate-600"].join(" ")}>
                      {lead.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
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
    stopped:   "bg-rose-100 text-rose-600",
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
// Main component
// ---------------------------------------------------------------------------

export default function CampaignDetailView({ campaignId }) {
  const router = useRouter();
  const { workspace } = useWorkspace();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("sequence");

  const workspaceId = workspace?.workspace_id;

  const fetchCampaign = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns/${campaignId}`,
        { credentials: "include" }
      );
      if (res.ok) setCampaign(await res.json());
    } catch {
      toast.error("Failed to load campaign.");
    } finally {
      setLoading(false);
    }
  }, [workspaceId, campaignId]);

  useEffect(() => { fetchCampaign(); }, [fetchCampaign]);

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
          <p className="text-xs text-slate-400">{campaign.lead_count} leads · {campaign.step_count} steps</p>
        </div>
        <span className={["rounded-full px-3 py-1 text-xs font-semibold capitalize", statusBadge[campaign.status] || "bg-slate-200 text-slate-700"].join(" ")}>
          {campaign.status}
        </span>
        <ExecutionControls
          campaign={campaign}
          workspaceId={workspaceId}
          onTransitioned={fetchCampaign}
        />
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
          <SequenceBuilder workspaceId={workspaceId} campaignId={campaignId} />
        )}
        {tab === "leads" && workspaceId && (
          <LeadsTab workspaceId={workspaceId} campaignId={campaignId} />
        )}
        {tab === "runs" && workspaceId && (
          <RunsTab workspaceId={workspaceId} campaignId={campaignId} />
        )}
      </div>
    </div>
  );
}
