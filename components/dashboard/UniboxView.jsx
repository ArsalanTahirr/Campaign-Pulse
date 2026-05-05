"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  Bolt,
  ChevronDown,
  Clock3,
  Inbox,
  Loader2,
  Mail,
  MailOpen,
  Search,
  Send,
  Tag,
  UserX,
} from "lucide-react";
import { toast } from "sonner";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import PermissionGate from "@/components/ui/PermissionGate";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Static config
// ---------------------------------------------------------------------------
const pipelineStatuses = [
  { id: "lead", label: "Lead", iconClass: "text-slate-400" },
  { id: "interested", label: "Interested", iconClass: "text-emerald-500" },
  { id: "meeting-booked", label: "Meeting booked", iconClass: "text-brand-600" },
  { id: "meeting-completed", label: "Meeting completed", iconClass: "text-amber-500" },
  { id: "won", label: "Won", iconClass: "text-lime-500" },
];

const moreOptions = [
  { id: "inbox", label: "All Messages", icon: Inbox },
  { id: "unread-only", label: "Unread only", icon: MailOpen },
  { id: "sent", label: "Sent", icon: Send },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function timeAgo(isoString) {
  if (!isoString) return "";
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(isoString).toLocaleDateString();
}

/** GET /workspaces/{id}/campaigns returns CampaignOut: field is `name`, not `campaign_name`. */
function campaignListLabel(c) {
  if (!c) return "";
  return c.name ?? c.campaign_name ?? "";
}

function selectionTitle(selection, campaigns, inboxes) {
  if (selection.type === "pipeline")
    return pipelineStatuses.find((s) => s.id === selection.id)?.label || "Pipeline";
  if (selection.type === "campaign")
    return campaignListLabel(campaigns.find((c) => c.campaign_id === selection.id)) || "Campaign";
  if (selection.type === "inbox")
    return inboxes.find((i) => i.inbox_id === selection.id)?.email || "Inbox";
  return moreOptions.find((o) => o.id === selection.id)?.label || "More";
}

function formatApiError(body) {
  const d = body?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === "object" && x?.msg ? x.msg : String(x)))
      .filter(Boolean)
      .join("; ");
  }
  return "Something went wrong.";
}

function mergeThreadFromPatchOut(prev, out, campaigns) {
  const campaignName = out.campaign_id
    ? campaignListLabel(campaigns.find((c) => c.campaign_id === out.campaign_id)) || null
    : null;
  return {
    ...prev,
    campaign_id: out.campaign_id,
    campaign_name: campaignName,
    pipeline_status: out.pipeline_status,
    lead: prev.lead
      ? { ...prev.lead, pipeline_status: out.pipeline_status ?? prev.lead.pipeline_status }
      : prev.lead,
  };
}

function ThreadMetadataControls({
  workspaceId,
  thread,
  campaigns,
  metaPatching,
  setMetaPatching,
  onThreadUpdated,
  interactionLocked,
}) {
  const pipelineValue =
    thread.lead?.pipeline_status || thread.pipeline_status || "lead";
  const campaignValue = thread.campaign_id || "";
  const selectClass =
    "max-w-[160px] truncate rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 outline-none focus:border-blue-300 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400";

  const patchThreadMeta = async (body) => {
    if (interactionLocked || metaPatching || !workspaceId) return;
    setMetaPatching(true);
    try {
      const r = await fetch(
        `${API}/workspaces/${workspaceId}/unibox/threads/${thread.thread_id}`,
        {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      );
      const payload = await r.json().catch(() => ({}));
      if (!r.ok) {
        toast.error(formatApiError(payload));
        return;
      }
      onThreadUpdated((prev) => mergeThreadFromPatchOut(prev, payload, campaigns));
    } catch {
      toast.error("Could not update thread.");
    } finally {
      setMetaPatching(false);
    }
  };

  const pipelineDisabled =
    interactionLocked || metaPatching || thread.is_orphan || !thread.lead;
  const campaignDisabled = interactionLocked || metaPatching;

  return (
    <>
      <select
        aria-label="Pipeline status"
        className={selectClass}
        disabled={pipelineDisabled}
        value={pipelineValue}
        onChange={(e) => patchThreadMeta({ pipeline_status: e.target.value })}
      >
        {pipelineStatuses.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label}
          </option>
        ))}
      </select>
      <select
        aria-label="Campaign tag"
        className={selectClass}
        disabled={campaignDisabled}
        value={campaignValue}
        onChange={(e) => {
          const v = e.target.value;
          patchThreadMeta({ campaign_id: v === "" ? null : v });
        }}
      >
        <option value="">No campaign</option>
        {campaigns.map((c) => (
          <option key={c.campaign_id} value={c.campaign_id}>
            {campaignListLabel(c)}
          </option>
        ))}
      </select>
    </>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
function Spinner() {
  return (
    <div className="flex h-full min-h-[200px] items-center justify-center">
      <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
    </div>
  );
}

function EmptyState({ label }) {
  return (
    <div className="flex min-h-[320px] flex-col items-center justify-center rounded-2xl border border-slate-100 bg-white p-8 text-center">
      <div className="relative mb-5 flex items-center justify-center">
        <motion.div
          className="absolute h-16 w-16 rounded-full bg-indigo-50"
          animate={{ scale: [1, 1.18, 1], opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          animate={{ scale: [1, 1.05, 1] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
        >
          <Inbox className="relative h-9 w-9 text-indigo-300" />
        </motion.div>
      </div>
      <p className="text-sm font-semibold text-slate-500">{label}</p>
      <p className="mt-1 text-sm italic font-medium text-slate-400">No conversations here yet.</p>
    </div>
  );
}

function PipelineBadge({ status }) {
  const map = {
    "lead": { label: "Lead", cls: "bg-slate-100 text-slate-500" },
    "interested": { label: "Interested", cls: "bg-emerald-50 text-emerald-600" },
    "meeting-booked": { label: "Meeting booked", cls: "bg-sky-50 text-sky-600" },
    "meeting-completed": { label: "Meeting completed", cls: "bg-amber-50 text-amber-600" },
    "won": { label: "Won", cls: "bg-lime-50 text-lime-700" },
  };
  const { label, cls } = map[status] || { label: status, cls: "bg-slate-100 text-slate-500" };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {label}
    </span>
  );
}

function ThreadCard({ thread, onClick }) {
  const isUnread = thread.unread_count > 0;
  return (
    <button
      type="button"
      onClick={() => onClick(thread)}
      className="w-full rounded-xl border border-slate-200 bg-slate-50/60 p-4 text-left transition-colors hover:bg-slate-100"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {isUnread && (
              <span className="inline-block h-2 w-2 shrink-0 rounded-full bg-blue-500" />
            )}
            <p className={`truncate text-sm ${isUnread ? "font-semibold text-slate-900" : "font-medium text-slate-700"}`}>
              {thread.contact_name}
            </p>
            {thread.is_orphan && (
              <UserX className="h-3.5 w-3.5 shrink-0 text-amber-400" title="Unknown sender" />
            )}
          </div>
          <p className="mt-1 truncate text-sm text-slate-500">{thread.subject}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {thread.pipeline_status && (
              <PipelineBadge status={thread.pipeline_status} />
            )}
            {thread.campaign_name && (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                <Tag className="h-3 w-3" />
                {thread.campaign_name}
              </span>
            )}
            {thread.unread_count > 0 && (
              <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-600">
                {thread.unread_count} unread
              </span>
            )}
          </div>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-1">
          <span className="text-xs text-slate-400">{timeAgo(thread.last_message_at)}</span>
          <span className="max-w-[100px] truncate text-right text-xs text-slate-400">
            {thread.inbox_email}
          </span>
        </div>
      </div>
    </button>
  );
}

function ThreadDetail({
  workspaceId,
  thread,
  campaigns,
  inboxes,
  onBack,
  onReplySent,
  onThreadUpdated,
}) {
  const colorByDirection = {
    outbound: "bg-blue-50 border-blue-100",
    inbound: "bg-white border-slate-200",
  };
  const alignByDirection = {
    outbound: "items-end",
    inbound: "items-start",
  };

  const messagesEndRef = useRef(null);
  const [metaPatching, setMetaPatching] = useState(false);
  const [readTogglingId, setReadTogglingId] = useState(null);

  // Reply state
  const [replyBody, setReplyBody] = useState("");
  const [fromAccountId, setFromAccountId] = useState(inboxes[0]?.inbox_id || "");
  const [isSending, setIsSending] = useState(false);
  const [replyError, setReplyError] = useState("");
  const [replySent, setReplySent] = useState(false);

  const readBusy = readTogglingId !== null;

  // Auto-select first inbox when inboxes load
  useEffect(() => {
    if (!fromAccountId && inboxes.length > 0) setFromAccountId(inboxes[0].inbox_id);
  }, [inboxes, fromAccountId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread.messages]);

  const toggleInboundRead = async (msg) => {
    if (!workspaceId || readBusy) return;
    const nextRead = !msg.is_read;
    setReadTogglingId(msg.message_id);
    try {
      const r = await fetch(
        `${API}/workspaces/${workspaceId}/unibox/threads/${thread.thread_id}/messages/${msg.message_id}/read`,
        {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ is_read: nextRead }),
        }
      );
      const payload = await r.json().catch(() => ({}));
      if (!r.ok) {
        toast.error(formatApiError(payload));
        return;
      }
      onThreadUpdated((prev) => ({
        ...prev,
        messages: prev.messages.map((m) =>
          m.message_id === msg.message_id ? { ...m, is_read: payload.is_read } : m
        ),
      }));
    } catch {
      toast.error("Could not update read state.");
    } finally {
      setReadTogglingId(null);
    }
  };

  const handleSend = async () => {
    if (!replyBody.trim()) { setReplyError("Reply body cannot be empty."); return; }
    if (!fromAccountId) { setReplyError("Please select a sender inbox."); return; }
    if (!workspaceId) { setReplyError("No workspace selected."); return; }
    setIsSending(true);
    setReplyError("");
    setReplySent(false);
    try {
      const r = await fetch(
        `${API}/workspaces/${workspaceId}/unibox/threads/${thread.thread_id}/reply`,
        {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ sender_account_id: fromAccountId, body_text: replyBody }),
        }
      );
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        setReplyError(err.detail || `Failed to send (${r.status}).`);
      } else {
        setReplyBody("");
        setReplySent(true);
        setTimeout(() => setReplySent(false), 3000);
        onReplySent?.();
      }
    } catch {
      setReplyError("Network error — could not send reply.");
    } finally {
      setIsSending(false);
    }
  };

  const metaProps = {
    workspaceId,
    thread,
    campaigns,
    metaPatching,
    setMetaPatching,
    onThreadUpdated,
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-slate-200 pb-4">
        <button
          type="button"
          onClick={onBack}
          className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">{thread.subject}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {thread.pipeline_status && <PipelineBadge status={thread.pipeline_status} />}
            {thread.campaign_name && (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                <Tag className="h-3 w-3" />
                {thread.campaign_name}
              </span>
            )}
            {thread.is_orphan && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-600">
                <UserX className="h-3 w-3" />
                Unknown sender
              </span>
            )}
            <PermissionGate
              action="manage_leads"
              fallback={
                <ThreadMetadataControls {...metaProps} interactionLocked />
              }
            >
              <ThreadMetadataControls {...metaProps} interactionLocked={false} />
            </PermissionGate>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="mt-4 flex-1 space-y-4 overflow-y-auto pr-1">
        {thread.messages?.map((msg) => (
          <div key={msg.message_id} className={`flex flex-col ${alignByDirection[msg.direction]}`}>
            <div className={`max-w-[85%] rounded-xl border p-4 ${colorByDirection[msg.direction]}`}>
              <div className="mb-2 flex items-center justify-between gap-4">
                <p className="text-xs font-semibold text-slate-600">
                  {msg.direction === "outbound" ? "You" : msg.from_address}
                </p>
                <span className="text-xs text-slate-400">
                  {timeAgo(msg.received_at || msg.sent_at || msg.created_at)}
                </span>
              </div>
              <p className="whitespace-pre-wrap text-sm text-slate-700">
                {msg.body_text || "(No plain-text body)"}
              </p>
              {msg.direction === "inbound" && (
                <div className="mt-2 flex items-center gap-2">
                  {!msg.is_read && (
                    <span className="inline-block rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-600">
                      Unread
                    </span>
                  )}
                  <button
                    type="button"
                    aria-label={msg.is_read ? "Mark as unread" : "Mark as read"}
                    title={msg.is_read ? "Mark as unread" : "Mark as read"}
                    disabled={readBusy}
                    onClick={() => toggleInboundRead(msg)}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {readTogglingId === msg.message_id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : msg.is_read ? (
                      <Mail className="h-3.5 w-3.5" />
                    ) : (
                      <MailOpen className="h-3.5 w-3.5" />
                    )}
                    {msg.is_read ? "Unread" : "Read"}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Reply composer */}
      <div className="mt-4 border-t border-slate-200 pt-4">
        {/* From selector */}
        {inboxes.length > 0 && (
          <div className="mb-3 flex items-center gap-2">
            <label className="shrink-0 text-xs font-medium text-slate-500">From:</label>
            <select
              value={fromAccountId}
              onChange={(e) => setFromAccountId(e.target.value)}
              className="flex-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-700 outline-none focus:border-blue-300"
            >
              {inboxes.map((inbox) => (
                <option key={inbox.inbox_id} value={inbox.inbox_id}>
                  {inbox.email}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Textarea */}
        <textarea
          value={replyBody}
          onChange={(e) => setReplyBody(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSend();
          }}
          rows={4}
          placeholder="Write a reply… (Ctrl+Enter to send)"
          className="w-full resize-none rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-300 focus:bg-white"
        />

        {/* Feedback + Send */}
        <div className="mt-2 flex items-center justify-between">
          <div>
            {replyError && (
              <p className="text-xs text-red-500">{replyError}</p>
            )}
            {replySent && (
              <p className="text-xs text-emerald-600">Reply sent!</p>
            )}
          </div>
          <button
            type="button"
            onClick={handleSend}
            disabled={isSending || !replyBody.trim()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {isSending ? "Sending…" : "Send Reply"}
          </button>
        </div>
      </div>
    </div>
  );
}

function SearchResultCard({ item }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-slate-900">{item.thread_subject}</p>
          <p className="mt-0.5 text-xs text-slate-500">{item.from_address}</p>
          {item.body_snippet && (
            <p className="mt-1 line-clamp-2 text-sm text-slate-600">{item.body_snippet}</p>
          )}
          <div className="mt-2 flex items-center gap-2">
            {item.campaign_name && (
              <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                <Tag className="h-3 w-3" />
                {item.campaign_name}
              </span>
            )}
            <span className="text-xs text-slate-400">{item.inbox_email}</span>
          </div>
        </div>
        <span className="shrink-0 text-xs text-slate-400">
          {timeAgo(item.received_at || item.created_at)}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function UniboxView() {
  const { workspace } = useWorkspace();
  const workspaceId = workspace?.workspace_id;

  // Sidebar data
  const [campaigns, setCampaigns] = useState([]);
  const [inboxes, setInboxes] = useState([]);

  // Thread list
  const [threads, setThreads] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  // Thread detail
  const [threadDetail, setThreadDetail] = useState(null);
  const [threadLoading, setThreadLoading] = useState(false);

  // Search
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchTotal, setSearchTotal] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [searchMode, setSearchMode] = useState(false);
  const searchRef = useRef(null);

  // Filter state
  const [activeSelection, setActiveSelection] = useState({ type: "pipeline", id: "lead" });
  const [isStatusOpen, setIsStatusOpen] = useState(true);
  const [isCampaignsOpen, setIsCampaignsOpen] = useState(false);
  const [isInboxesOpen, setIsInboxesOpen] = useState(false);
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const [statusSearch, setStatusSearch] = useState("");
  const [campaignSearch, setCampaignSearch] = useState("");
  const [inboxSearch, setInboxSearch] = useState("");

  // ── Load campaigns + inboxes ──────────────────────────────────────────────
  useEffect(() => {
    if (!workspaceId) return;

    fetch(`${API}/workspaces/${workspaceId}/campaigns`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setCampaigns(Array.isArray(data) ? data : []))
      .catch(() => { });

    fetch(`${API}/workspaces/${workspaceId}/unibox/inboxes`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : { items: [] }))
      .then((d) => setInboxes(d.items || []))
      .catch(() => { });
  }, [workspaceId]);

  // ── Build thread query URL ────────────────────────────────────────────────
  const threadQueryUrl = useMemo(() => {
    if (!workspaceId) return null;
    const p = new URLSearchParams({ page_size: "50" });
    if (activeSelection.type === "pipeline") {
      p.set("pipeline_status", activeSelection.id);
    } else if (activeSelection.type === "campaign") {
      p.set("campaign_id", activeSelection.id);
    } else if (activeSelection.type === "inbox") {
      p.set("inbox_id", activeSelection.id);
    } else if (activeSelection.type === "more") {
      if (activeSelection.id === "unread-only") p.set("view", "unread");
      else if (activeSelection.id === "sent") p.set("view", "sent");
      else p.set("view", "all");
    }
    return `${API}/workspaces/${workspaceId}/unibox/threads?${p}`;
  }, [workspaceId, activeSelection]);

  // ── Fetch threads when filter changes ────────────────────────────────────
  useEffect(() => {
    if (!threadQueryUrl || searchMode) return;
    setLoading(true);
    setThreadDetail(null);

    fetch(threadQueryUrl, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : { total: 0, items: [] }))
      .then((d) => { setThreads(d.items || []); setTotal(d.total || 0); })
      .catch(() => { setThreads([]); setTotal(0); })
      .finally(() => setLoading(false));
  }, [threadQueryUrl, searchMode]);

  // ── Open thread detail ────────────────────────────────────────────────────
  const openThread = useCallback(
    async (thread) => {
      if (!workspaceId) return;
      setThreadLoading(true);
      try {
        const r = await fetch(
          `${API}/workspaces/${workspaceId}/unibox/threads/${thread.thread_id}`,
          { credentials: "include" }
        );
        if (r.ok) setThreadDetail(await r.json());
      } catch { }
      setThreadLoading(false);
    },
    [workspaceId]
  );

  // ── Search ────────────────────────────────────────────────────────────────
  const doSearch = useCallback(async () => {
    const q = searchQuery.trim();
    if (!workspaceId || !q) return;
    setIsSearching(true);
    try {
      const r = await fetch(
        `${API}/workspaces/${workspaceId}/unibox/search?q=${encodeURIComponent(q)}&page_size=50`,
        { credentials: "include" }
      );
      if (r.ok) {
        const d = await r.json();
        setSearchResults(d.items || []);
        setSearchTotal(d.total || 0);
      }
    } catch { }
    setIsSearching(false);
  }, [workspaceId, searchQuery]);

  const handleSearchKeyDown = (e) => {
    if (e.key === "Enter") doSearch();
    if (e.key === "Escape") { setSearchMode(false); setSearchQuery(""); }
  };

  // ── Filter helpers ────────────────────────────────────────────────────────
  const filteredStatuses = useMemo(() => {
    const q = statusSearch.trim().toLowerCase();
    return q ? pipelineStatuses.filter((s) => s.label.toLowerCase().includes(q)) : pipelineStatuses;
  }, [statusSearch]);

  const filteredCampaigns = useMemo(() => {
    const q = campaignSearch.trim().toLowerCase();
    return q
      ? campaigns.filter((c) => campaignListLabel(c).toLowerCase().includes(q))
      : campaigns;
  }, [campaignSearch, campaigns]);

  const filteredInboxes = useMemo(() => {
    const q = inboxSearch.trim().toLowerCase();
    return q ? inboxes.filter((i) => i.email.toLowerCase().includes(q)) : inboxes;
  }, [inboxSearch, inboxes]);

  const activeLabel = selectionTitle(activeSelection, campaigns, inboxes);

  // ── Sidebar nav item click ────────────────────────────────────────────────
  const selectFilter = (type, id) => {
    setActiveSelection({ type, id });
    setThreadDetail(null);
    setSearchMode(false);
    setSearchQuery("");
  };

  // ── Render ────────────────────────────────────────────────────────────────
  const renderMainContent = () => {
    // Search mode
    if (searchMode) {
      return (
        <>
          <div className="flex items-center justify-between border-b border-slate-200 pb-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Search Results
              </p>
              <h2 className="text-xl font-semibold text-slate-900">
                {searchQuery ? `"${searchQuery}"` : "Search messages"}
              </h2>
            </div>
            {searchTotal > 0 && (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                {searchTotal} result{searchTotal !== 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="mt-4 flex-1">
            {isSearching ? (
              <Spinner />
            ) : searchResults.length === 0 ? (
              <EmptyState label={searchQuery ? `No results for "${searchQuery}"` : "Type a keyword and press Enter"} />
            ) : (
              <div className="space-y-3">
                {searchResults.map((item) => (
                  <SearchResultCard key={item.message_id} item={item} />
                ))}
              </div>
            )}
          </div>
        </>
      );
    }

    // Thread detail
    if (threadDetail) {
      return (
        <ThreadDetail
          workspaceId={workspaceId}
          thread={threadDetail}
          campaigns={campaigns}
          inboxes={inboxes}
          onBack={() => setThreadDetail(null)}
          onReplySent={() => openThread(threadDetail)}
          onThreadUpdated={(fn) => setThreadDetail((prev) => (prev ? fn(prev) : prev))}
        />
      );
    }
    if (threadLoading) return <Spinner />;

    // Thread list
    return (
      <>
        <div className="flex items-center justify-between border-b border-slate-200 pb-4">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest text-indigo-600">
              Active View
            </p>
            <h2 className="text-3xl font-black tracking-tight text-slate-900">{activeLabel}</h2>
          </div>
          <div className="flex items-center gap-2">
            {total > 0 && (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                {total} thread{total !== 1 ? "s" : ""}
              </span>
            )}
            <div className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600">
              <Clock3 className="h-3.5 w-3.5" />
              Live
            </div>
          </div>
        </div>

        <div className="mt-4 flex-1">
          {loading ? (
            <Spinner />
          ) : threads.length === 0 ? (
            <EmptyState label={activeLabel} />
          ) : (
            <div className="space-y-3">
              {threads.map((thread) => (
                <ThreadCard key={thread.thread_id} thread={thread} onClick={openThread} />
              ))}
            </div>
          )}
        </div>
      </>
    );
  };

  return (
    <section className="flex flex-1 bg-white p-4 sm:p-6">
      <div className="flex w-full flex-col gap-4 lg:flex-row">

        {/* ── Sidebar ── */}
        <aside className="w-full rounded-2xl border border-slate-100 bg-slate-50/50 p-4 shadow-sm backdrop-blur-md lg:w-[280px] lg:shrink-0">

          {/* Search bar */}
          <div className="relative mb-4">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              ref={searchRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => setSearchMode(true)}
              onKeyDown={handleSearchKeyDown}
              placeholder="Search messages…"
              className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none transition-all duration-200 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:bg-slate-800 dark:border-slate-700"
            />
          </div>

          {/* Status */}
          <div>
            <button
              type="button"
              onClick={() => setIsStatusOpen((p) => !p)}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs font-bold uppercase tracking-widest text-indigo-600 transition-colors hover:bg-indigo-50/60"
            >
              <span>Status</span>
              <ChevronDown
                className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${isStatusOpen ? "rotate-180" : ""}`}
              />
            </button>

            <AnimatePresence initial={false}>
              {isStatusOpen && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="relative mt-2">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      value={statusSearch}
                      onChange={(e) => setStatusSearch(e.target.value)}
                      placeholder="Search status"
                      className="h-9 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-600 outline-none transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                    />
                  </div>
                  <div className="mt-2 space-y-0.5">
                    {filteredStatuses.map((status) => {
                      const isActive = activeSelection.type === "pipeline" && activeSelection.id === status.id;
                      return (
                        <button
                          key={status.id}
                          type="button"
                          onClick={() => selectFilter("pipeline", status.id)}
                          className={`relative flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                            isActive ? "text-indigo-700" : "text-slate-600 hover:bg-slate-100/70"
                          }`}
                        >
                          {isActive && (
                            <motion.div
                              layoutId="activeStatusPill"
                              className="absolute inset-0 rounded-xl bg-indigo-50 border border-indigo-100"
                              transition={{ type: "spring", stiffness: 380, damping: 32 }}
                            />
                          )}
                          <span className="relative">
                            <Bolt className={`h-4 w-4 ${status.iconClass}`} />
                          </span>
                          <span className="relative font-semibold">{status.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Campaigns */}
          <div className="mt-4 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={() => setIsCampaignsOpen((p) => !p)}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs font-bold uppercase tracking-widest text-indigo-600 transition-colors hover:bg-indigo-50/60"
            >
              <span>All Campaigns</span>
              <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform ${isCampaignsOpen ? "rotate-180" : ""}`} />
            </button>

            <AnimatePresence initial={false}>
              {isCampaignsOpen && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="relative mt-2">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      value={campaignSearch}
                      onChange={(e) => setCampaignSearch(e.target.value)}
                      placeholder="Search campaigns"
                      className="h-9 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-600 outline-none transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                    />
                  </div>
                  <div className="mt-2 space-y-0.5">
                    {filteredCampaigns.length > 0 ? (
                      filteredCampaigns.map((c) => {
                        const isActive = activeSelection.type === "campaign" && activeSelection.id === c.campaign_id;
                        return (
                          <button
                            key={c.campaign_id}
                            type="button"
                            onClick={() => selectFilter("campaign", c.campaign_id)}
                            className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition-colors ${isActive ? "bg-blue-50 text-blue-600" : "text-slate-700 hover:bg-slate-50"
                              }`}
                          >
                            <span className="truncate">{campaignListLabel(c)}</span>
                          </button>
                        );
                      })
                    ) : (
                      <p className="px-3 py-2 text-xs text-slate-400">No campaigns found.</p>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Inboxes */}
          <div className="mt-4 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={() => setIsInboxesOpen((p) => !p)}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs font-bold uppercase tracking-widest text-indigo-600 transition-colors hover:bg-indigo-50/60"
            >
              <span>All Inboxes</span>
              <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform ${isInboxesOpen ? "rotate-180" : ""}`} />
            </button>

            <AnimatePresence initial={false}>
              {isInboxesOpen && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="relative mt-2">
                    <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      value={inboxSearch}
                      onChange={(e) => setInboxSearch(e.target.value)}
                      placeholder="Search inboxes"
                      className="h-9 w-full rounded-xl border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-600 outline-none transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20"
                    />
                  </div>
                  <div className="mt-2 space-y-0.5">
                    {filteredInboxes.length > 0 ? (
                      filteredInboxes.map((inbox) => {
                        const isActive = activeSelection.type === "inbox" && activeSelection.id === inbox.inbox_id;
                        return (
                          <button
                            key={inbox.inbox_id}
                            type="button"
                            onClick={() => selectFilter("inbox", inbox.inbox_id)}
                            className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors ${isActive ? "bg-blue-50 text-blue-600" : "text-slate-700 hover:bg-slate-50"
                              }`}
                          >
                            <span className="truncate">{inbox.email}</span>
                            {inbox.unread_count > 0 && (
                              <span className="ml-2 shrink-0 rounded-full bg-blue-100 px-1.5 py-0.5 text-xs font-medium text-blue-600">
                                {inbox.unread_count}
                              </span>
                            )}
                          </button>
                        );
                      })
                    ) : (
                      <p className="px-3 py-2 text-xs text-slate-400">No inboxes found.</p>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* More */}
          <div className="mt-4 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={() => setIsMoreOpen((p) => !p)}
              className="flex w-full items-center justify-between rounded-xl px-3 py-2.5 text-left text-xs font-bold uppercase tracking-widest text-indigo-600 transition-colors hover:bg-indigo-50/60"
            >
              <span>More</span>
              <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform ${isMoreOpen ? "rotate-180" : ""}`} />
            </button>

            <AnimatePresence initial={false}>
              {isMoreOpen && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="mt-2 space-y-0.5">
                    {moreOptions.map((opt) => {
                      const Icon = opt.icon;
                      const isActive = activeSelection.type === "more" && activeSelection.id === opt.id;
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => selectFilter("more", opt.id)}
                          className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${isActive ? "bg-blue-50 text-blue-600" : "text-slate-700 hover:bg-slate-50"
                            }`}
                        >
                          <Icon className="h-4 w-4" />
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </aside>

        {/* ── Main panel ── */}
        <div className="flex min-h-[420px] flex-1 flex-col rounded-2xl border border-slate-100 bg-white p-4 shadow-sm sm:p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={searchMode ? "search" : threadDetail ? threadDetail.thread_id : `${activeSelection.type}:${activeSelection.id}`}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.18 }}
              className="flex w-full flex-col"
            >
              {renderMainContent()}
            </motion.div>
          </AnimatePresence>
        </div>

      </div>
    </section>
  );
}
