"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Mail,
  Search,
  SlidersHorizontal,
  MoreHorizontal,
  Plus,
  Pencil,
  RefreshCcw,
  Save,
  Trash2,
  XCircle,
  Zap,
  Inbox,
  Server,
  Gauge,
  Flame,
  X,
} from "lucide-react";
import { toast } from "sonner";
import PermissionGate from "@/components/ui/PermissionGate";
import { useWorkspace } from "@/contexts/WorkspaceContext";
import { messageFromApiErrorBody, userMessageFromFetchError } from "@/utils/apiError";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ACCOUNT_FORM_DRAFT_KEY_PREFIX = "email-account-form-draft";

const defaultForm = {
  provider_type: "smtp",
  email: "",
  smtp_host: "",
  smtp_port: 587,
  imap_host: "",
  imap_port: 993,
  app_password: "",
  daily_sending_limit: 100,
  min_delay_seconds: 60,
  max_imap_fetch: 100,
  warmup_settings: {
    is_warmup_active: false,
    start_mail_rate: 5,
    daily_max_emails: 50,
    ramp_up_rate: 1.5,
  },
};

const PROVIDER_OPTIONS = [
  { value: "smtp", label: "SMTP" },
  { value: "google", label: "Google Workspace / Gmail" },
  { value: "microsoft", label: "Microsoft 365 / Outlook" },
];

const PROVIDER_PRESETS = {
  google: {
    smtp_host: "smtp.gmail.com",
    smtp_port: 587,
    imap_host: "imap.gmail.com",
    imap_port: 993,
  },
  microsoft: {
    smtp_host: "smtp.office365.com",
    smtp_port: 587,
    imap_host: "outlook.office365.com",
    imap_port: 993,
  },
};

const STATUS_META = {
  active: {
    label: "Active",
    classes: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200",
  },
  warming_up: {
    label: "Warming up",
    classes: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200",
  },
  suspended: {
    label: "Suspended",
    classes: "bg-rose-100 text-rose-800 dark:bg-rose-900/30 dark:text-rose-200",
  },
  disconnected: {
    label: "Disconnected",
    classes: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
};

/** Instantly-style section shell */
function SectionCard({ icon: Icon, title, description, children, headerRight = null, allowOverflow = false }) {
  return (
    <section
      className={[
        allowOverflow ? "overflow-visible" : "overflow-hidden",
        "rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900",
      ].join(" ")}
    >
      <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-start sm:justify-between dark:border-slate-800">
        <div className="flex min-w-0 gap-3">
          {Icon ? (
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Icon className="h-5 w-5" />
            </div>
          ) : null}
          <div className="min-w-0">
            <h2 className="text-base font-semibold tracking-tight text-slate-900 dark:text-slate-100">{title}</h2>
            {description ? <p className="mt-1 max-w-2xl text-sm leading-relaxed text-slate-500 dark:text-slate-400 break-words">{description}</p> : null}
          </div>
        </div>
        {headerRight ? <div className="flex w-full min-w-0 flex-wrap items-center gap-2 sm:w-auto sm:justify-end">{headerRight}</div> : null}
      </div>
      <div className="p-5 sm:p-6">{children}</div>
    </section>
  );
}

function Subsection({ title, description, children }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-950/40">
      <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">{title}</h3>
      {description ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{description}</p> : null}
      <div className="mt-4 space-y-4">{children}</div>
    </div>
  );
}

function LabelField({ label, hint, children }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</label>
      {children}
      {hint ? <p className="text-xs text-slate-400 dark:text-slate-500">{hint}</p> : null}
    </div>
  );
}

const inputClass =
  "h-10 w-full rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition-colors focus:border-blue-400 focus:ring-1 focus:ring-blue-400/30 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

function AccountForm({ value, onChange, saving, onSubmit, onCancel, mode }) {
  function handleProviderChange(nextProviderType) {
    const preset = PROVIDER_PRESETS[nextProviderType];
    if (!preset) {
      onChange({ ...value, provider_type: nextProviderType });
      return;
    }
    onChange({
      ...value,
      provider_type: nextProviderType,
      smtp_host: preset.smtp_host,
      smtp_port: preset.smtp_port,
      imap_host: preset.imap_host,
      imap_port: preset.imap_port,
    });
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5">
      <Subsection
        title="Account identity"
        description="The address campaigns send from and how we label this mailbox in the system."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <LabelField label="Email address" hint="Must match your provider mailbox.">
            <input required className={inputClass} type="email" autoComplete="email" value={value.email} onChange={(e) => onChange({ ...value, email: e.target.value })} placeholder="you@company.com" />
          </LabelField>
          <LabelField label="Provider type" hint="Usually smtp, google, or microsoft.">
            <select className={inputClass} value={value.provider_type} onChange={(e) => handleProviderChange(e.target.value)}>
              {PROVIDER_OPTIONS.map((provider) => (
                <option key={provider.value} value={provider.value}>
                  {provider.label}
                </option>
              ))}
            </select>
          </LabelField>
        </div>
      </Subsection>

      <Subsection
        title="Mail servers (SMTP & IMAP)"
        description="Outbound SMTP sends campaign mail. IMAP is used to detect replies from leads."
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <LabelField label="SMTP host" hint="e.g. smtp.gmail.com">
            <input required className={inputClass} value={value.smtp_host} onChange={(e) => onChange({ ...value, smtp_host: e.target.value })} placeholder="smtp.example.com" />
          </LabelField>
          <LabelField label="SMTP port" hint="587 (STARTTLS) or 465 (SSL)">
            <input required className={inputClass} type="number" value={value.smtp_port} onChange={(e) => onChange({ ...value, smtp_port: Number(e.target.value) })} />
          </LabelField>
          <LabelField label="IMAP host" hint="e.g. imap.gmail.com">
            <input required className={inputClass} value={value.imap_host} onChange={(e) => onChange({ ...value, imap_host: e.target.value })} placeholder="imap.example.com" />
          </LabelField>
          <LabelField label="IMAP port" hint="Typically 993 (SSL)">
            <input required className={inputClass} type="number" value={value.imap_port} onChange={(e) => onChange({ ...value, imap_port: Number(e.target.value) })} />
          </LabelField>
          <div className="sm:col-span-2">
            <LabelField label="App password / SMTP password" hint="Use an app-specific password when your provider requires it. Leave blank when editing if unchanged.">
              <input required={mode !== "edit"} className={inputClass} type="password" autoComplete="new-password" value={value.app_password} onChange={(e) => onChange({ ...value, app_password: e.target.value })} placeholder="••••••••" />
            </LabelField>
          </div>
        </div>
      </Subsection>

      <Subsection
        title="Sending limits & safety"
        description="Caps and pacing reduce spam risk and protect your domain reputation."
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <LabelField label="Daily sending limit" hint="Max sends per day from this mailbox.">
            <input className={inputClass} type="number" min={1} value={value.daily_sending_limit} onChange={(e) => onChange({ ...value, daily_sending_limit: Number(e.target.value) })} />
          </LabelField>
          <LabelField label="Min delay (seconds)" hint="Minimum wait between consecutive sends.">
            <input className={inputClass} type="number" min={0} value={value.min_delay_seconds} onChange={(e) => onChange({ ...value, min_delay_seconds: Number(e.target.value) })} />
          </LabelField>
          <LabelField label="Max IMAP messages / run" hint="How many inbox messages to scan per reply check.">
            <input className={inputClass} type="number" min={1} value={value.max_imap_fetch} onChange={(e) => onChange({ ...value, max_imap_fetch: Number(e.target.value) })} />
          </LabelField>
        </div>
      </Subsection>

      <Subsection
        title="Warmup (optional)"
        description="Gradually increases daily volume for new or cold mailboxes. Peer warmup sends between your connected accounts."
      >
        <div className="flex flex-wrap items-center gap-4 border-b border-slate-100 pb-4 dark:border-slate-800">
          <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              checked={Boolean(value.warmup_settings?.is_warmup_active)}
              onChange={(e) =>
                onChange({
                  ...value,
                  warmup_settings: { ...value.warmup_settings, is_warmup_active: e.target.checked },
                })
              }
            />
            Enable warmup for this account
          </label>
        </div>
        <div className="grid gap-4 pt-4 sm:grid-cols-3">
          <LabelField label="Start mail rate (day 1)" hint="Emails on the first warmup day.">
            <input className={inputClass} type="number" step="0.1" min={0} value={value.warmup_settings?.start_mail_rate ?? 5} onChange={(e) => onChange({ ...value, warmup_settings: { ...value.warmup_settings, start_mail_rate: Number(e.target.value) } })} />
          </LabelField>
          <LabelField label="Ramp multiplier" hint="Each day: previous × this (e.g. 1.5).">
            <input className={inputClass} type="number" step="0.1" min={0.1} value={value.warmup_settings?.ramp_up_rate ?? 1.5} onChange={(e) => onChange({ ...value, warmup_settings: { ...value.warmup_settings, ramp_up_rate: Number(e.target.value) } })} />
          </LabelField>
          <LabelField label="Warmup daily cap" hint="Ceiling during warmup (before your global daily limit).">
            <input className={inputClass} type="number" min={1} value={value.warmup_settings?.daily_max_emails ?? 50} onChange={(e) => onChange({ ...value, warmup_settings: { ...value.warmup_settings, daily_max_emails: Number(e.target.value) } })} />
          </LabelField>
        </div>
      </Subsection>

      <div className="flex flex-col-reverse gap-2 border-t border-slate-100 pt-5 sm:flex-row sm:justify-end dark:border-slate-800">
        <button type="button" onClick={onCancel} className="rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-800">
          Cancel
        </button>
        <button type="submit" disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60">
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {mode === "edit" ? "Save changes" : "Add email account"}
        </button>
      </div>
    </form>
  );
}

export default function EmailAccountsView() {
  const { workspace } = useWorkspace();
  const [accounts, setAccounts] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [formMode, setFormMode] = useState("create");
  const [editingAccountId, setEditingAccountId] = useState(null);
  const [formData, setFormData] = useState(defaultForm);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [pendingDeleteAccount, setPendingDeleteAccount] = useState(null);
  const [engineStatus, setEngineStatus] = useState(null);
  const [opLoading, setOpLoading] = useState("");
  const [accountSearch, setAccountSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [openActionMenuFor, setOpenActionMenuFor] = useState(null);
  const [campaignDrawer, setCampaignDrawer] = useState(null);

  const getDraftStorageKey = useCallback(() => {
    const workspaceId = workspace?.workspace_id || "unknown";
    return `${ACCOUNT_FORM_DRAFT_KEY_PREFIX}:${workspaceId}`;
  }, [workspace?.workspace_id]);

  const fetchAccounts = useCallback(async ({ silent = false } = {}) => {
    if (!workspace?.workspace_id) return;
    if (!silent) {
      setLoading(true);
      setError("");
    }
    try {
      const res = await fetch(`${API}/workspaces/${workspace.workspace_id}/email-accounts`, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to load email accounts.");
      setAccounts(await res.json());
    } catch (err) {
      if (!silent) {
        setError(err.message);
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, [workspace?.workspace_id]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const fetchCampaigns = useCallback(async () => {
    if (!workspace?.workspace_id) return;
    try {
      const res = await fetch(`${API}/workspaces/${workspace.workspace_id}/campaigns`, { credentials: "include" });
      if (!res.ok) return;
      setCampaigns(await res.json());
    } catch {
      // non-fatal
    }
  }, [workspace?.workspace_id]);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  const fetchEngineStatus = useCallback(async () => {
    if (!workspace?.workspace_id) return;
    try {
      const res = await fetch(`${API}/workspaces/${workspace.workspace_id}/engine/status`, { credentials: "include" });
      if (!res.ok) return;
      setEngineStatus(await res.json());
    } catch {
      // non-fatal
    }
  }, [workspace?.workspace_id]);

  useEffect(() => {
    fetchEngineStatus();
  }, [fetchEngineStatus]);

  useEffect(() => {
    function handleOutsideClick() {
      setOpenActionMenuFor(null);
    }
    if (!openActionMenuFor) return undefined;
    document.addEventListener("click", handleOutsideClick);
    return () => document.removeEventListener("click", handleOutsideClick);
  }, [openActionMenuFor]);

  const hasAccounts = useMemo(() => accounts.length > 0, [accounts.length]);
  const filteredAccounts = useMemo(() => {
    return accounts.filter((account) => {
      const matchesSearch = !accountSearch.trim()
        || account.email.toLowerCase().includes(accountSearch.trim().toLowerCase());
      const matchesStatus = statusFilter === "all" || account.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [accounts, accountSearch, statusFilter]);
  const campaignNamesByAccountId = useMemo(() => {
    const map = new Map();
    for (const campaign of campaigns) {
      const campaignName = campaign.name || "Untitled campaign";
      for (const sender of campaign.sender_accounts || []) {
        const existing = map.get(sender.account_id) || [];
        existing.push(campaignName);
        map.set(sender.account_id, existing);
      }
    }
    return map;
  }, [campaigns]);

  async function handleSave(event) {
    event.preventDefault();
    if (!workspace?.workspace_id) return;
    setSaving(true);
    try {
      const payload = {
        ...formData,
        email: formData.email.trim(),
        provider_type: (formData.provider_type || "smtp").trim().toLowerCase(),
      };
      delete payload.status;
      delete payload.is_verified;
      const warmupPayload = payload.warmup_settings;
      delete payload.warmup_settings;
      const url = editingAccountId
        ? `${API}/workspaces/${workspace.workspace_id}/email-accounts/${editingAccountId}`
        : `${API}/workspaces/${workspace.workspace_id}/email-accounts`;
      const res = await fetch(url, {
        method: editingAccountId ? "PATCH" : "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(
          messageFromApiErrorBody(err, editingAccountId ? "Failed to update email account." : "Failed to add email account.")
        );
      }
      const account = await res.json();
      if (warmupPayload) {
        await fetch(`${API}/workspaces/${workspace.workspace_id}/email-accounts/${account.account_id}/warmup`, {
          method: "PATCH",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(warmupPayload),
        });
      }
      toast.success(editingAccountId ? "Email account updated." : "Email account added.");
      if (!editingAccountId && typeof window !== "undefined") {
        window.sessionStorage.removeItem(getDraftStorageKey());
      }
      setShowForm(false);
      setFormData(defaultForm);
      setEditingAccountId(null);
      setFormMode("create");
      await fetchAccounts();
      await fetchCampaigns();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, editingAccountId ? "Failed to update account." : "Failed to add account."));
    } finally {
      setSaving(false);
    }
  }

  function openEditForm(account) {
    setFormMode("edit");
    setEditingAccountId(account.account_id);
    setFormData({
      ...defaultForm,
      ...account,
      provider_type: (account.provider_type || "smtp").toLowerCase(),
      app_password: "",
      warmup_settings: {
        ...defaultForm.warmup_settings,
        ...(account.warmup_settings || {}),
      },
    });
    setShowForm(true);
  }

  function openCreateForm() {
    setFormMode("create");
    setEditingAccountId(null);
    if (typeof window !== "undefined") {
      const raw = window.sessionStorage.getItem(getDraftStorageKey());
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          setFormData({ ...defaultForm, ...parsed, warmup_settings: { ...defaultForm.warmup_settings, ...(parsed.warmup_settings || {}) } });
        } catch {
          setFormData(defaultForm);
        }
      } else {
        setFormData(defaultForm);
      }
    } else {
      setFormData(defaultForm);
    }
    setShowForm(true);
  }

  function closeFormDrawer() {
    setShowForm(false);
    setFormMode("create");
    setEditingAccountId(null);
    setFormData(defaultForm);
  }

  useEffect(() => {
    if (formMode !== "create") return;
    if (!showForm) return;
    if (typeof window === "undefined") return;
    window.sessionStorage.setItem(getDraftStorageKey(), JSON.stringify(formData));
  }, [formData, formMode, getDraftStorageKey, showForm]);

  async function handleDelete(accountId) {
    if (!workspace?.workspace_id) return;
    setDeletingId(accountId);
    try {
      const res = await fetch(`${API}/workspaces/${workspace.workspace_id}/email-accounts/${accountId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to delete account.");
      setAccounts((prev) => prev.filter((acc) => acc.account_id !== accountId));
      toast.success("Email account deleted.");
      await fetchCampaigns();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to delete account."));
    } finally {
      setDeletingId(null);
      setPendingDeleteAccount(null);
    }
  }

  async function handleToggleWarmup(account) {
    if (!workspace?.workspace_id) return;
    try {
      const next = !account.warmup_settings?.is_warmup_active;
      // Optimistic update to avoid full-table loading flicker.
      setAccounts((prev) =>
        prev.map((acc) => {
          if (acc.account_id !== account.account_id) return acc;
          return {
            ...acc,
            status: next ? "warming_up" : "active",
            warmup_settings: {
              ...(acc.warmup_settings || {}),
              is_warmup_active: next,
            },
          };
        })
      );
      const res = await fetch(`${API}/workspaces/${workspace.workspace_id}/email-accounts/${account.account_id}/warmup`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_warmup_active: next }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(messageFromApiErrorBody(err, "Failed to update warmup."));
      }
      toast.success(`Warmup ${next ? "enabled" : "disabled"} for ${account.email}.`);
      await fetchAccounts({ silent: true });
      await fetchCampaigns();
    } catch (err) {
      // Re-sync if request failed after optimistic UI.
      await fetchAccounts({ silent: true });
      toast.error(userMessageFromFetchError(err, "Failed to update warmup."));
    }
  }

  async function runEngineOp(kind) {
    if (!workspace?.workspace_id) return;
    setOpLoading(kind);
    try {
      const endpoint = { send: "run-send-once", warmup: "run-warmup-once", imap: "run-imap-once" }[kind];
      const res = await fetch(`${API}/workspaces/${workspace.workspace_id}/engine/${endpoint}`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) throw new Error("Operation failed.");
      const data = await res.json();
      if (kind === "send") toast.success(`Processed ${data.processed} lead(s).`);
      if (kind === "warmup") toast.success(`Warmup sent ${data.warmup_sent} email(s).`);
      if (kind === "imap") toast.success(`Detected ${data.replies_detected} reply event(s).`);
      await fetchAccounts();
      await fetchCampaigns();
      await fetchEngineStatus();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Engine operation failed."));
    } finally {
      setOpLoading("");
    }
  }

  async function toggleEngineEnabled(nextEnabled) {
    if (!workspace?.workspace_id) return;
    setOpLoading("toggle-engine");
    try {
      const res = await fetch(`${API}/workspaces/${workspace.workspace_id}/engine/enabled`, {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: nextEnabled }),
      });
      if (!res.ok) throw new Error("Failed to toggle engine.");
      setEngineStatus((prev) => (prev ? { ...prev, engine_enabled: nextEnabled } : prev));
      toast.success(`Auto-send ${nextEnabled ? "enabled" : "disabled"}.`);
      await fetchEngineStatus();
    } catch (err) {
      toast.error(userMessageFromFetchError(err, "Failed to update auto-send setting."));
    } finally {
      setOpLoading("");
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-6 sm:px-6 lg:px-8">
      <header className="space-y-1">
        <p className="text-xs font-medium uppercase tracking-wider text-slate-400 dark:text-slate-500">Workspace</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">Email accounts</h1>
        <p className="max-w-2xl text-sm text-slate-600 dark:text-slate-400">
          Connect inboxes your campaigns send from. Configure limits and warmup, then use the engine tools to process the queue or scan for replies.
        </p>
      </header>

      {/* —— Section 1: Engine —— */}
      <SectionCard
        icon={Zap}
        title="Sending engine"
        description="Background workers process queued leads when enabled. Use the buttons below to run a single cycle now (useful for testing)."
        headerRight={
          <>
            {engineStatus ? (
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span
                  className={[
                    "inline-flex items-center rounded-full px-2.5 py-1 font-medium",
                    engineStatus.engine_enabled ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200" : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
                  ].join(" ")}
                >
                  {engineStatus.engine_enabled ? "Auto-send on" : "Auto-send off"}
                </span>
                <span className="rounded-full bg-slate-100 px-2.5 py-1 font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                  Queue: {engineStatus.queued_leads} waiting
                </span>
                {engineStatus.sending_leads > 0 ? (
                  <span className="rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-900 dark:bg-amber-900/30 dark:text-amber-200">
                    {engineStatus.sending_leads} in progress
                  </span>
                ) : null}
                <PermissionGate action="manage_email_accounts">
                  <button
                    type="button"
                    onClick={() => toggleEngineEnabled(!engineStatus.engine_enabled)}
                    disabled={opLoading === "toggle-engine"}
                    className={[
                      "rounded-full px-2.5 py-1 font-medium transition-colors",
                      engineStatus.engine_enabled
                        ? "bg-emerald-600 text-white hover:bg-emerald-700"
                        : "bg-slate-200 text-slate-700 hover:bg-slate-300 dark:bg-slate-700 dark:text-slate-200",
                    ].join(" ")}
                  >
                    {opLoading === "toggle-engine"
                      ? "Saving..."
                      : engineStatus.engine_enabled
                        ? "Disable auto-send"
                        : "Enable auto-send"}
                  </button>
                </PermissionGate>
              </div>
            ) : null}
            <button
              type="button"
              onClick={() => {
                fetchAccounts();
                fetchEngineStatus();
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <RefreshCcw className="h-4 w-4" />
              Refresh status
            </button>
          </>
        }
      >
        <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
          Set <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[11px] dark:bg-slate-800">ENABLE_SENDING_ENGINE=true</code> on the API server for continuous processing.
        </p>
        <div className="flex flex-wrap gap-2">
          <PermissionGate action="manage_email_accounts">
            <button
              type="button"
              onClick={() => runEngineOp("send")}
              disabled={opLoading === "send"}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm hover:bg-slate-50 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
            >
              {opLoading === "send" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mail className="h-4 w-4 text-blue-600" />}
              Run send once
            </button>
          </PermissionGate>
          <PermissionGate action="manage_email_accounts">
            <button
              type="button"
              onClick={() => runEngineOp("warmup")}
              disabled={opLoading === "warmup"}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm hover:bg-slate-50 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
            >
              {opLoading === "warmup" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Flame className="h-4 w-4 text-orange-500" />}
              Run warmup once
            </button>
          </PermissionGate>
          <PermissionGate action="manage_email_accounts">
            <button
              type="button"
              onClick={() => runEngineOp("imap")}
              disabled={opLoading === "imap"}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-800 shadow-sm hover:bg-slate-50 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-800"
            >
              {opLoading === "imap" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Inbox className="h-4 w-4 text-slate-600" />}
              Scan inboxes (IMAP)
            </button>
          </PermissionGate>
        </div>
      </SectionCard>

      {/* —— Section 2: Account list —— */}
      <SectionCard
        icon={Server}
        title="Your email accounts"
        description="All senders available to this workspace. Add accounts here, then attach them to a campaign’s sender pool."
        allowOverflow
        headerRight={
          <PermissionGate action="manage_email_accounts">
            <button
              type="button"
              onClick={openCreateForm}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Add email account
            </button>
          </PermissionGate>
        }
      >
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        ) : error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">{error}</div>
        ) : !hasAccounts ? (
          <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-slate-200 bg-slate-50/80 py-14 text-center dark:border-slate-700 dark:bg-slate-900/50">
            <Mail className="h-12 w-12 text-slate-300 dark:text-slate-600" />
            <div>
              <p className="font-medium text-slate-800 dark:text-slate-200">No accounts yet</p>
              <p className="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">Add your first mailbox to start sending. You can connect Gmail, Outlook, or any SMTP provider.</p>
            </div>
            <PermissionGate action="manage_email_accounts">
              <button type="button" onClick={openCreateForm} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
                Add your first account
              </button>
            </PermissionGate>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50/50 p-3 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800 dark:bg-slate-900/40">
              <div className="relative w-full sm:max-w-xs">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <input
                  value={accountSearch}
                  onChange={(e) => setAccountSearch(e.target.value)}
                  placeholder="Search account..."
                  className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none focus:border-blue-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                />
              </div>
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="h-4 w-4 text-slate-400" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 outline-none focus:border-blue-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
                >
                  <option value="all">All statuses</option>
                  <option value="active">Active</option>
                  <option value="warming_up">Warming up</option>
                  <option value="suspended">Suspended</option>
                  <option value="disconnected">Disconnected</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto overflow-y-visible rounded-xl border border-slate-100 dark:border-slate-800">
              <div className="min-w-[940px]">
                <div className="grid grid-cols-[minmax(240px,1.6fr)_140px_140px_130px_80px] border-b border-slate-100 bg-slate-50 px-4 py-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:bg-slate-800/70 dark:text-slate-400">
                  <div>Email</div>
                  <div>Emails sent</div>
                  <div>Warmup emails</div>
                  <div>Campaigns</div>
                  <div className="text-right">Actions</div>
                </div>
                <div className="divide-y divide-slate-100 dark:divide-slate-800">
                  {filteredAccounts.map((account) => {
                    const names = campaignNamesByAccountId.get(account.account_id) || [];
                    const warmupOn = Boolean(account.warmup_settings?.is_warmup_active);
                    const warmupEmails = warmupOn ? Math.min(account.sent_count_today, account.daily_sending_limit) : 0;
                    return (
                      <div key={account.account_id} className="grid grid-cols-[minmax(240px,1.6fr)_140px_140px_130px_80px] items-center px-4 py-4">
                        <div className="min-w-0">
                          <div className="truncate font-semibold text-slate-900 dark:text-slate-100">{account.email}</div>
                          <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                            <span>{account.provider_type}</span>
                            {(() => {
                              const meta = STATUS_META[account.status] || STATUS_META.active;
                              return <span className={["inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold", meta.classes].join(" ")}>{meta.label}</span>;
                            })()}
                          </div>
                        </div>
                        <div className="text-sm font-medium text-slate-700 dark:text-slate-300">
                          {account.sent_count_today} of {account.daily_sending_limit}
                        </div>
                        <div className="text-sm font-medium text-slate-700 dark:text-slate-300">{warmupEmails}</div>
                        <div className="text-xs text-slate-500">
                          {names.length > 0 ? (
                            <button
                              type="button"
                              onClick={() =>
                                setCampaignDrawer({
                                  email: account.email,
                                  names,
                                })
                              }
                              className="inline-flex items-center rounded-md bg-slate-100 px-2 py-1 font-medium text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
                            >
                              {names.length} campaign{names.length === 1 ? "" : "s"}
                            </button>
                          ) : (
                            "Not set"
                          )}
                        </div>
                        <div className="flex items-center justify-end gap-1">
                          <PermissionGate action="manage_email_accounts">
                            <button
                              type="button"
                              onClick={() => handleToggleWarmup(account)}
                              title={warmupOn ? "Pause warmup" : "Enable warmup"}
                              className={[
                                "rounded-md p-1.5 transition-colors",
                                warmupOn
                                  ? "text-emerald-600 hover:bg-emerald-50 dark:text-emerald-300 dark:hover:bg-emerald-900/20"
                                  : "text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200",
                              ].join(" ")}
                            >
                              <Flame className="h-4 w-4" />
                            </button>
                          </PermissionGate>
                          <PermissionGate action="manage_email_accounts">
                            <div className="relative">
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  setOpenActionMenuFor((prev) => (prev === account.account_id ? null : account.account_id));
                                }}
                                className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-300"
                                aria-label="More actions"
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </button>
                              {openActionMenuFor === account.account_id ? (
                                <div
                                  className="absolute bottom-8 right-0 z-50 w-36 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-900"
                                  onClick={(event) => event.stopPropagation()}
                                >
                                  <button
                                    type="button"
                                    onClick={() => {
                                      openEditForm(account);
                                      setOpenActionMenuFor(null);
                                    }}
                                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                                  >
                                    <Pencil className="h-4 w-4" />
                                    Edit
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      setPendingDeleteAccount(account);
                                      setOpenActionMenuFor(null);
                                    }}
                                    disabled={deletingId === account.account_id}
                                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-rose-600 hover:bg-rose-50 disabled:opacity-50 dark:hover:bg-rose-950/40"
                                  >
                                    {deletingId === account.account_id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                                    Delete
                                  </button>
                                </div>
                              ) : null}
                            </div>
                          </PermissionGate>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            {filteredAccounts.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 py-12 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                No accounts match your search/filter.
              </div>
            ) : null}
          </div>
        )}
      </SectionCard>

      {/* —— Right drawer: Add / Edit account —— */}
      <div
        className={[
          "fixed inset-0 z-[80] transition-opacity duration-300",
          showForm ? "pointer-events-auto bg-slate-950/25 backdrop-blur-[1px]" : "pointer-events-none bg-transparent",
        ].join(" ")}
        onClick={closeFormDrawer}
        aria-hidden={!showForm}
      >
        <aside
          className={[
            "absolute right-0 top-0 h-screen w-full max-w-2xl overflow-hidden rounded-l-2xl border-l border-slate-200/80 bg-white shadow-2xl transition-transform duration-300 ease-out dark:border-slate-800 dark:bg-slate-900",
            showForm ? "translate-x-0" : "translate-x-full",
          ].join(" ")}
          onClick={(event) => event.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-label={formMode === "edit" ? "Edit email account" : "Add email account"}
        >
          <div className="flex h-full flex-col">
            <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
              <div className="flex min-w-0 gap-3">
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                  <Gauge className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-base font-semibold tracking-tight text-slate-900 dark:text-slate-100">
                    {formMode === "edit" ? "Edit email account" : "Add email account"}
                  </h2>
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                    Fill each block in order. Credentials are stored for sending and reply detection only.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={closeFormDrawer}
                className="shrink-0 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
              >
                Close
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 sm:p-6">
              <AccountForm
                value={formData}
                onChange={setFormData}
                saving={saving}
                mode={formMode}
                onSubmit={handleSave}
                onCancel={closeFormDrawer}
              />
            </div>
          </div>
        </aside>
      </div>

      {/* Delete confirmation modal */}
      <div
        className={[
          "fixed inset-0 z-[90] transition-opacity duration-200",
          pendingDeleteAccount ? "pointer-events-auto bg-slate-950/30 backdrop-blur-[1px]" : "pointer-events-none bg-transparent",
        ].join(" ")}
        aria-hidden={!pendingDeleteAccount}
      >
        <div className="flex min-h-full items-center justify-center p-4">
          <div
            className={[
              "w-full max-w-md rounded-2xl border border-slate-200 bg-white p-5 shadow-2xl transition-all duration-200 dark:border-slate-800 dark:bg-slate-900",
              pendingDeleteAccount ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
            ].join(" ")}
            role="dialog"
            aria-modal="true"
            aria-label="Delete email account confirmation"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-lg bg-rose-100 p-2 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">
                <AlertTriangle className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">Delete email account</h3>
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                  This will remove{" "}
                  <span className="font-medium text-slate-900 dark:text-slate-200">
                    {pendingDeleteAccount?.email || "this account"}
                  </span>
                  {" "}from this workspace.
                </p>
              </div>
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPendingDeleteAccount(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-200 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => pendingDeleteAccount && handleDelete(pendingDeleteAccount.account_id)}
                disabled={!pendingDeleteAccount || deletingId === pendingDeleteAccount.account_id}
                className="inline-flex items-center gap-2 rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-700 disabled:opacity-60"
              >
                {pendingDeleteAccount && deletingId === pendingDeleteAccount.account_id ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Delete account
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Campaign membership drawer */}
      <div
        className={[
          "fixed inset-0 z-[75] transition-opacity duration-300",
          campaignDrawer ? "pointer-events-auto bg-slate-950/20" : "pointer-events-none bg-transparent",
        ].join(" ")}
        onClick={() => setCampaignDrawer(null)}
        aria-hidden={!campaignDrawer}
      >
        <aside
          className={[
            "absolute right-0 top-0 h-screen w-full max-w-md border-l border-slate-200 bg-white shadow-2xl transition-transform duration-300 ease-out dark:border-slate-800 dark:bg-slate-900",
            campaignDrawer ? "translate-x-0" : "translate-x-full",
          ].join(" ")}
          onClick={(event) => event.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-label="Campaign membership list"
        >
          <div className="flex h-full flex-col">
            <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-5 py-4 dark:border-slate-800">
              <div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">Connected campaigns</h3>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 break-all">{campaignDrawer?.email}</p>
              </div>
              <button
                type="button"
                onClick={() => setCampaignDrawer(null)}
                className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                aria-label="Close campaign drawer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              {campaignDrawer?.names?.length ? (
                <ul className="space-y-2">
                  {campaignDrawer.names.map((name) => (
                    <li key={name} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-200">
                      {name}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500 dark:text-slate-400">No campaigns linked yet.</p>
              )}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
