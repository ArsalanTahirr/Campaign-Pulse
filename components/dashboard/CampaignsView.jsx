"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Loader2,
  Pause,
  Play,
  Plus,
  Trash2,
  Search,
  X,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import PermissionGate from "@/components/ui/PermissionGate";
import { messageFromApiErrorBody, userMessageFromFetchError } from "@/utils/apiError";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const statusOptions = [
  { label: "All statuses", value: "all", icon: Zap, iconClass: "text-slate-500" },
  { label: "Active", value: "active", icon: Play, iconClass: "text-blue-600" },
  { label: "Paused", value: "paused", icon: Pause, iconClass: "text-amber-500" },
  { label: "Error", value: "error", icon: AlertTriangle, iconClass: "text-rose-500" },
  { label: "Completed", value: "completed", icon: CheckCircle2, iconClass: "text-emerald-600" },
];

const sortOptions = [
  { label: "Newest first", value: "newest" },
  { label: "Oldest first", value: "oldest" },
  { label: "Name A–Z", value: "name-asc" },
  { label: "Name Z–A", value: "name-desc" },
];

const statusBadgeClasses = {
  active:    "bg-blue-600 text-white",
  completed: "bg-emerald-600 text-white",
  draft:     "bg-slate-200 text-slate-700",
  paused:    "bg-amber-500 text-white",
  error:     "bg-rose-500 text-white",
  evergreen: "bg-sky-600 text-white",
};

function toTitleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

// ---------------------------------------------------------------------------
// Create Campaign Modal
// ---------------------------------------------------------------------------

function CreateCampaignModal({ workspaceId, onCreated, onClose }) {
  const [name, setName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspaceId}/campaigns`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: name.trim() }),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to create campaign."));
      }
      const created = await res.json();
      toast.success(`Campaign "${created.name}" created!`);
      onCreated(created);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            New Campaign
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Campaign name
            </label>
            <input
              autoFocus
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q2 Outreach — SaaS CTOs"
              className="h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
            />
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !name.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Create Campaign
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function CampaignsView() {
  const router = useRouter();
  const { workspace } = useWorkspace();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [isStatusOpen, setIsStatusOpen] = useState(false);
  const [isSortOpen, setIsSortOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState(statusOptions[0]);
  const [selectedSort, setSelectedSort] = useState(sortOptions[0]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const statusRef = useRef(null);
  const sortRef = useRef(null);

  const fetchCampaigns = useCallback(async () => {
    if (!workspace) return;
    setLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspace.workspace_id}/campaigns`,
        { credentials: "include" }
      );
      if (!res.ok) throw new Error("Failed to load campaigns.");
      const data = await res.json();
      setCampaigns(data);
    } catch (err) {
      setFetchError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspace]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (statusRef.current && !statusRef.current.contains(event.target)) setIsStatusOpen(false);
      if (sortRef.current && !sortRef.current.contains(event.target)) setIsSortOpen(false);
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  async function handleToggleCampaign(campaign) {
    const action = campaign.status === "active" ? "paused" : "started";
    const permission = action === "paused" ? "pause_campaign" : "start_campaign";
    setActionLoading(campaign.campaign_id);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspace.workspace_id}/campaigns/${campaign.campaign_id}/runs`,
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
      toast.success(`Campaign ${action === "paused" ? "paused" : "started"}.`);
      await fetchCampaigns();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  async function handleDeleteCampaign(campaign) {
    if (
      !window.confirm(
        `Delete “${campaign.name}”? It will be removed from this workspace.`
      )
    ) {
      return;
    }
    setDeletingId(campaign.campaign_id);
    try {
      const res = await fetch(
        `${API}/workspaces/${workspace.workspace_id}/campaigns/${campaign.campaign_id}`,
        { method: "DELETE", credentials: "include" }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to delete campaign."));
      }
      setCampaigns((prev) => prev.filter((c) => c.campaign_id !== campaign.campaign_id));
      toast.success(`Campaign “${campaign.name}” deleted.`);
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to delete campaign."));
    } finally {
      setDeletingId(null);
    }
  }

  const filteredCampaigns = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase();
    const base = campaigns.filter((c) => {
      const statusMatch = selectedStatus.value === "all" || c.status === selectedStatus.value;
      const nameMatch = c.name.toLowerCase().includes(normalized);
      return statusMatch && nameMatch;
    });
    const sorted = [...base];
    if (selectedSort.value === "newest") sorted.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    if (selectedSort.value === "oldest") sorted.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    if (selectedSort.value === "name-asc") sorted.sort((a, b) => a.name.localeCompare(b.name));
    if (selectedSort.value === "name-desc") sorted.sort((a, b) => b.name.localeCompare(a.name));
    return sorted;
  }, [campaigns, searchTerm, selectedSort.value, selectedStatus.value]);

  const SelectedStatusIcon = selectedStatus.icon;

  return (
    <section className="flex flex-1 flex-col gap-5 bg-slate-50/60 px-6 py-6 sm:px-8">
      {showCreateModal && workspace && (
        <CreateCampaignModal
          workspaceId={workspace.workspace_id}
          onCreated={(created) => {
            setCampaigns((prev) => [created, ...prev]);
            setShowCreateModal(false);
            router.push(`/dashboard/campaigns/${created.campaign_id}`);
          }}
          onClose={() => setShowCreateModal(false)}
        />
      )}

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search campaigns…"
            className="h-10 w-full rounded-xl border border-slate-200/60 bg-slate-50/50 pl-9 pr-3 text-sm text-slate-700 outline-none transition-all duration-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-slate-700/50 dark:bg-slate-900 dark:text-slate-300"
          />
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <div className="relative" ref={statusRef}>
            <button
              type="button"
              onClick={() => { setIsStatusOpen((p) => !p); setIsSortOpen(false); }}
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200/60 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition-all duration-200 hover:border-indigo-400/50 hover:bg-indigo-50/30 dark:border-slate-700/50 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-indigo-900/10"
            >
              <SelectedStatusIcon className={["h-4 w-4", selectedStatus.iconClass].join(" ")} />
              <span>{selectedStatus.label}</span>
              <ChevronDown className={["h-4 w-4 text-slate-400 transition-transform duration-200", isStatusOpen ? "rotate-180" : ""].join(" ")} />
            </button>
            <AnimatePresence>
              {isStatusOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -5 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: -5 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute right-0 top-11 z-20 w-52 rounded-xl border border-slate-200/60 bg-white p-1 shadow-xl shadow-slate-200/60 dark:border-slate-700/50 dark:bg-slate-900 dark:shadow-slate-900/60"
                >
                  {statusOptions.map((option) => {
                    const Icon = option.icon;
                    return (
                      <button
                        key={option.value}
                        type="button"
                        onClick={() => { setSelectedStatus(option); setIsStatusOpen(false); }}
                        className={["flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors duration-150", selectedStatus.value === option.value ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300" : "text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"].join(" ")}
                      >
                        <Icon className={["h-4 w-4", option.iconClass].join(" ")} />
                        {option.label}
                      </button>
                    );
                  })}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="relative" ref={sortRef}>
            <button
              type="button"
              onClick={() => { setIsSortOpen((p) => !p); setIsStatusOpen(false); }}
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200/60 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition-all duration-200 hover:border-indigo-400/50 hover:bg-indigo-50/30 dark:border-slate-700/50 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-indigo-900/10"
            >
              <span>{selectedSort.label}</span>
              <ChevronDown className={["h-4 w-4 text-slate-400 transition-transform duration-200", isSortOpen ? "rotate-180" : ""].join(" ")} />
            </button>
            <AnimatePresence>
              {isSortOpen && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: -5 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: -5 }}
                  transition={{ duration: 0.15, ease: "easeOut" }}
                  className="absolute right-0 top-11 z-20 w-44 rounded-xl border border-slate-200/60 bg-white p-1 shadow-xl shadow-slate-200/60 dark:border-slate-700/50 dark:bg-slate-900 dark:shadow-slate-900/60"
                >
                  {sortOptions.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => { setSelectedSort(option); setIsSortOpen(false); }}
                      className={["w-full rounded-lg px-2.5 py-2 text-left text-sm transition-colors duration-150", selectedSort.value === option.value ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300" : "text-slate-700 hover:bg-slate-50 dark:text-slate-300 dark:hover:bg-slate-800"].join(" ")}
                    >
                      {option.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <PermissionGate action="create_campaign">
            <button
              type="button"
              onClick={() => setShowCreateModal(true)}
              className="inline-flex h-10 items-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all duration-200 hover:bg-indigo-500 active:scale-95"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add New
            </button>
          </PermissionGate>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50/40 p-3">
        <div className="min-w-[980px]">
          <div className="mb-2 grid grid-cols-[minmax(200px,1.5fr)_130px_90px_90px_170px_100px] items-center px-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            <div>Name</div>
            <div>Status</div>
            <div>Steps</div>
            <div>Leads</div>
            <div>Sender accounts</div>
            <div />
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : fetchError ? (
            <div className="py-12 text-center">
              <p className="text-sm font-medium text-rose-600">{fetchError}</p>
              <button
                type="button"
                onClick={fetchCampaigns}
                className="mt-3 rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
              >
                Retry
              </button>
            </div>
          ) : filteredCampaigns.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <motion.div
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              >
                <Image
                  src="/campaignDood.png"
                  alt="No campaigns"
                  width={500}
                  height={500}
                  className="h-auto w-full max-w-[300px] opacity-60 mix-blend-multiply"
                  priority
                />
              </motion.div>
              <p className="mt-3 text-xl font-bold text-slate-900 dark:text-slate-100">
                {campaigns.length === 0
                  ? "Add a campaign to start sending emails"
                  : "No campaigns match your filters"}
              </p>
              {campaigns.length === 0 && (
                <PermissionGate action="create_campaign">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(true)}
                    className="mt-5 inline-flex items-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all duration-200 hover:bg-indigo-500 active:scale-95"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    Add New
                  </button>
                </PermissionGate>
              )}
            </div>
          ) : (
            filteredCampaigns.map((campaign) => (
              <div
                key={campaign.campaign_id}
                role="button"
                tabIndex={0}
                onClick={() => router.push(`/dashboard/campaigns/${campaign.campaign_id}`)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    router.push(`/dashboard/campaigns/${campaign.campaign_id}`);
                  }
                }}
                className="mb-3 grid cursor-pointer grid-cols-[minmax(200px,1.5fr)_130px_90px_90px_170px_100px] items-center rounded-xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700 shadow-sm transition-all hover:border-blue-200 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40"
              >
                <div className="font-semibold text-slate-800">{campaign.name}</div>

                <div>
                  <span
                    className={[
                      "inline-flex rounded-full px-2.5 py-1 text-xs font-semibold",
                      statusBadgeClasses[campaign.status] || "bg-slate-200 text-slate-700",
                    ].join(" ")}
                  >
                    {toTitleCase(campaign.status)}
                  </span>
                </div>

                <div className="text-slate-600">{campaign.step_count}</div>
                <div className="text-slate-600">{campaign.lead_count}</div>
                <div className="text-xs text-slate-600">
                  {(campaign.sender_accounts || []).length > 0 ? (
                    <span title={(campaign.sender_accounts || []).map((s) => s.email).join(", ")}>
                      {(campaign.sender_accounts || []).length} connected
                    </span>
                  ) : (
                    <span className="text-amber-600">Not connected</span>
                  )}
                </div>

                <div className="ml-auto flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <PermissionGate action={campaign.status === "active" ? "pause_campaign" : "start_campaign"}>
                    <button
                      type="button"
                      disabled={
                        actionLoading === campaign.campaign_id ||
                        !["active", "draft", "paused"].includes(campaign.status) ||
                        (campaign.status !== "active" && (campaign.lead_count ?? 0) < 1)
                      }
                      title={
                        campaign.status !== "active" && (campaign.lead_count ?? 0) < 1
                          ? "Add at least one lead before starting or resuming."
                          : undefined
                      }
                      onClick={() => handleToggleCampaign(campaign)}
                      className="rounded-md p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700 disabled:opacity-40"
                      aria-label={campaign.status === "active" ? "Pause campaign" : "Start campaign"}
                    >
                      {actionLoading === campaign.campaign_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : campaign.status === "active" ? (
                        <Pause className="h-4 w-4" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                    </button>
                  </PermissionGate>
                  <PermissionGate action="delete_campaign">
                    <button
                      type="button"
                      disabled={deletingId === campaign.campaign_id}
                      onClick={() => handleDeleteCampaign(campaign)}
                      className="rounded-md p-1.5 text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-600 disabled:opacity-40"
                      aria-label="Delete campaign"
                      title="Delete campaign"
                    >
                      {deletingId === campaign.campaign_id ? (
                        <Loader2 className="h-4 w-4 animate-spin text-rose-500" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </button>
                  </PermissionGate>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
