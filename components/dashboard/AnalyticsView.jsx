"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import {
  Calendar,
  CheckCircle2,
  ChevronDown,
  Filter,
  Info,
  Layers,
  Loader2,
  Mail,
  MessageCircle,
  MousePointerClick,
  Pause,
  Play,
  Search,
  Send,
  Zap,
} from "lucide-react";
import AnalyticsDateRangeCalendar from "@/components/dashboard/AnalyticsDateRangeCalendar";
import { useWorkspace } from "@/contexts/WorkspaceContext";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/** Graph API grouping; UI control removed — keep requests consistent. */
const ANALYTICS_CHART_GRANULARITY = "daily";

async function readApiError(res) {
  try {
    const body = await res.json();
    const d = body?.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join("; ");
    if (d != null) return JSON.stringify(d);
  } catch {
    /* ignore */
  }
  return res.statusText || `HTTP ${res.status}`;
}

const RANGE_PRESETS = [
  { id: "7d", label: "Last 7 days" },
  { id: "mtd", label: "Month to date" },
  { id: "4w", label: "Last 4 weeks" },
  { id: "3m", label: "Last 3 months" },
  { id: "6m", label: "Last 6 months" },
  { id: "12m", label: "Last 12 months" },
  { id: "all", label: "All time" },
  { id: "custom", label: "Custom" },
];

const STATUS_FILTER_OPTIONS = [
  { id: "all", label: "All statuses", Icon: Zap },
  { id: "active", label: "Active", Icon: Play },
  { id: "paused", label: "Paused", Icon: Pause },
  { id: "completed", label: "Completed", Icon: CheckCircle2 },
];

function matchesLifecycle(lifecycle, filter) {
  const L = (lifecycle || "").toString().toLowerCase();
  if (!filter || filter === "all") return true;
  if (filter === "active") return L === "active";
  if (filter === "paused") return L === "paused";
  if (filter === "completed") return ["completed", "archived", "deleted"].includes(L);
  return true;
}

function computeDateRangeUtc(preset, customFromYmd, customToYmd) {
  if (preset === "custom" && customFromYmd && customToYmd) {
    const start = new Date(`${customFromYmd}T00:00:00.000Z`);
    const end = new Date(`${customToYmd}T23:59:59.999Z`);
    return { dateFrom: start.toISOString(), dateTo: end.toISOString() };
  }
  if (preset === "custom") {
    return { dateFrom: null, dateTo: null };
  }
  if (preset === "all") {
    return { dateFrom: null, dateTo: null };
  }
  const end = new Date();
  end.setUTCHours(23, 59, 59, 999);
  const start = new Date(end);
  start.setUTCHours(0, 0, 0, 0);
  if (preset === "7d") {
    start.setUTCDate(end.getUTCDate() - 6);
  } else if (preset === "mtd") {
    start.setUTCFullYear(end.getUTCFullYear(), end.getUTCMonth(), 1);
    start.setUTCHours(0, 0, 0, 0);
  } else if (preset === "4w") {
    start.setUTCDate(end.getUTCDate() - 27);
  } else if (preset === "3m") {
    start.setTime(end.getTime());
    start.setUTCMonth(start.getUTCMonth() - 3);
  } else if (preset === "6m") {
    start.setTime(end.getTime());
    start.setUTCMonth(start.getUTCMonth() - 6);
  } else if (preset === "12m") {
    start.setTime(end.getTime());
    start.setUTCMonth(start.getUTCMonth() - 12);
  }
  return { dateFrom: start.toISOString(), dateTo: end.toISOString() };
}

function buildSummaryQuery(filterCampaignId, dateRangePreset, customFromYmd, customToYmd, campaignStatus) {
  const { dateFrom, dateTo } = computeDateRangeUtc(dateRangePreset, customFromYmd, customToYmd);
  const p = new URLSearchParams();
  if (filterCampaignId) p.set("campaign_id", filterCampaignId);
  if (dateFrom) p.set("date_from", dateFrom);
  if (dateTo) p.set("date_to", dateTo);
  if (campaignStatus && campaignStatus !== "all") p.set("campaign_status", campaignStatus);
  const qs = p.toString();
  return qs ? `?${qs}` : "";
}

function buildGraphQuery(filterCampaignId, dateRangePreset, customFromYmd, customToYmd, campaignStatus) {
  const { dateFrom, dateTo } = computeDateRangeUtc(dateRangePreset, customFromYmd, customToYmd);
  const p = new URLSearchParams();
  p.set("granularity", ANALYTICS_CHART_GRANULARITY);
  if (filterCampaignId) p.set("campaign_id", filterCampaignId);
  if (dateFrom) p.set("date_from", dateFrom);
  if (dateTo) p.set("date_to", dateTo);
  if (campaignStatus && campaignStatus !== "all") p.set("campaign_status", campaignStatus);
  return `?${p.toString()}`;
}

// Exactly 4 series as required.
const seriesMeta = [
  { key: "total_sent", label: "Total Emails Sent", tone: "text-amber-500" },
  { key: "open_rate", label: "Open Rate (%)", tone: "text-sky-500" },
  { key: "click_rate", label: "Click Rate (%)", tone: "text-emerald-500" },
  { key: "reply_rate", label: "Reply Rate (%)", tone: "text-fuchsia-600" },
];

const metricByKey = seriesMeta.reduce((acc, item) => {
  acc[item.key] = item;
  return acc;
}, {});

const cardVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } },
};

function KpiCard({ icon: Icon, iconBg, toneClass, bgClass, title, value, subValue }) {
  return (
    <motion.div
      variants={cardVariants}
      whileHover={{ scale: 1.02, translateY: -2 }}
      className={["group rounded-3xl border border-slate-200/60 p-6 shadow-sm transition-all hover:shadow-md", bgClass].join(" ")}
    >
      <div className="flex items-start justify-between">
        <div className={["flex h-10 w-10 items-center justify-center rounded-2xl", iconBg].join(" ")}>
          <Icon className={["h-5 w-5", toneClass].join(" ")} />
        </div>
        <Info className="h-3.5 w-3.5 text-slate-300" />
      </div>
      <p className="mt-4 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">{title}</p>
      <p className="mt-1 text-4xl font-black tracking-tight text-slate-900">{value}</p>
      {subValue ? <p className="mt-1 text-xs font-medium text-slate-400">{subValue}</p> : null}
    </motion.div>
  );
}

function AnalyticsTooltip({ active, label, payload }) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div className="min-w-[190px] rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-lg">
      <p className="mb-2 text-xs font-semibold text-slate-700">{label}</p>
      <div className="space-y-1">
        {payload.map((point, index) => {
          const meta = metricByKey[point.dataKey];
          if (!meta) {
            return null;
          }
          return (
            <div key={`${meta.key}-${index}`} className="flex items-center justify-between gap-3 text-xs text-slate-600">
              <span className="inline-flex items-center gap-2">
                <span className={["h-2 w-2 rounded-full", meta.tone.replace("text", "bg")].join(" ")} />
                {meta.label}
              </span>
              <span className="font-semibold text-slate-800">{point.value}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChartLegend() {
  return (
    <div className="flex flex-wrap items-center justify-center gap-4 pb-3">
      {seriesMeta.map((item) => (
        <div key={item.key} className="inline-flex items-center gap-2 text-xs font-medium text-slate-600">
          <span className={["h-2 w-2 rounded-full", item.tone.replace("text", "bg")].join(" ")} />
          {item.label}
        </div>
      ))}
    </div>
  );
}

function AnalyticsChartCard({ chartData, emptyHint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <ChartLegend />
      {chartData.length === 0 && emptyHint ? (
        <div className="flex h-[300px] items-center justify-center px-4 text-center text-sm text-slate-500">
          {emptyHint}
        </div>
      ) : (
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 16, right: 40, left: -20, bottom: 8 }}>
              <XAxis dataKey="label" tickLine={false} axisLine={{ stroke: "rgb(203 213 225)" }} tick={{ fill: "rgb(100 116 139)", fontSize: 11 }} />
              <YAxis
                yAxisId="left"
                allowDecimals={false}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "rgb(148 163 184)", fontSize: 11 }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "rgb(148 163 184)", fontSize: 11 }}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                content={<AnalyticsTooltip />}
                cursor={{ stroke: "rgb(148 163 184)", strokeDasharray: "4 4" }}
              />

              <Area yAxisId="left" type="monotone" dataKey="total_sent" fill="rgb(245 158 11 / 0.12)" stroke="none" isAnimationActive />
              <Line yAxisId="left" type="monotone" dataKey="total_sent" stroke="#f59e0b" strokeWidth={2} dot={false} isAnimationActive />
              <Line yAxisId="right" type="monotone" dataKey="open_rate" stroke="#0ea5e9" strokeWidth={2} dot={false} isAnimationActive />
              <Line yAxisId="right" type="monotone" dataKey="click_rate" stroke="#10b981" strokeWidth={2} dot={false} isAnimationActive />
              <Line yAxisId="right" type="monotone" dataKey="reply_rate" stroke="#c026d3" strokeWidth={2} dot={false} isAnimationActive />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Campaign analytics table
// ---------------------------------------------------------------------------

const tableRowVariants = {
  hidden: { opacity: 0, x: -10 },
  visible: (i) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.06, duration: 0.3, ease: [0.22, 1, 0.36, 1] },
  }),
};

function CampaignAnalyticsTable({ campaigns }) {
  if (!campaigns || campaigns.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mt-5 flex flex-col items-center justify-center rounded-2xl border border-dashed border-indigo-100 bg-indigo-50/30 px-4 py-14 text-center"
      >
        <motion.div
          animate={{ scale: [1, 1.08, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-100"
        >
          <Layers className="h-6 w-6 text-indigo-400" />
        </motion.div>
        <p className="text-sm font-semibold text-slate-500">No campaign data available</p>
        <p className="mt-1 text-xs italic text-slate-400">Data will appear once campaigns have activity.</p>
      </motion.div>
    );
  }

  return (
    <div className="mt-5 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            {["Campaign", "Status", "Sequence Started", "Opened", "Replied", "Opportunities"].map((h, i) => (
              <th
                key={h}
                className={`py-3 text-xs font-bold uppercase tracking-[0.12em] text-indigo-400 ${
                  i === 0 ? "pr-4 text-left" : i < 2 ? "pr-4 text-left" : "pr-4 text-right last:pr-0"
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {campaigns.map((row, i) => (
            <motion.tr
              key={row.campaign_id}
              custom={i}
              variants={tableRowVariants}
              initial="hidden"
              animate="visible"
              whileHover={{ backgroundColor: "rgba(238,242,255,0.6)" }}
              className="group border-b border-slate-50 transition-colors"
            >
              <td className="py-3.5 pr-4 font-semibold text-slate-800">{row.campaign_name}</td>
              <td className="py-3.5 pr-4">
                <span className={[
                  "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide",
                  row.status === "active"
                    ? "bg-emerald-50 text-emerald-600"
                    : row.status === "paused"
                    ? "bg-amber-50 text-amber-600"
                    : "bg-slate-100 text-slate-500"
                ].join(" ")}>
                  <span className={`mr-1.5 h-1.5 w-1.5 rounded-full ${
                    row.status === "active" ? "bg-emerald-500" : row.status === "paused" ? "bg-amber-500" : "bg-slate-400"
                  }`} />
                  {row.status}
                </span>
              </td>
              <td className="py-3.5 pr-4 text-right font-medium text-slate-700">{row.sequence_started}</td>
              <td className="py-3.5 pr-4 text-right font-medium text-slate-700">{row.opened}</td>
              <td className="py-3.5 pr-4 text-right font-medium text-slate-700">
                {row.replied.count}
                <span className="ml-1 text-xs text-slate-400">({row.replied.rate}%)</span>
              </td>
              <td className="py-3.5 text-right font-medium text-slate-700">{row.opportunities}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Account performance table
// ---------------------------------------------------------------------------

function AccountPerformanceTable({ rows }) {
  if (!rows || rows.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="mt-5 flex flex-col items-center justify-center rounded-2xl border border-dashed border-indigo-100 bg-indigo-50/30 px-4 py-14 text-center"
      >
        <motion.div
          animate={{ scale: [1, 1.08, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-100"
        >
          <Mail className="h-6 w-6 text-indigo-400" />
        </motion.div>
        <p className="text-sm font-semibold text-slate-500">No account data for this campaign</p>
        <p className="mt-1 text-xs italic text-slate-400">Select a campaign above to see account-level breakdown.</p>
      </motion.div>
    );
  }

  return (
    <div className="mt-5 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            {["Sending Account", "Contacted", "Opened", "Replied"].map((h, i) => (
              <th
                key={h}
                className={`py-3 text-xs font-bold uppercase tracking-[0.12em] text-indigo-400 ${
                  i === 0 ? "pr-4 text-left" : "pr-4 text-right last:pr-0"
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <motion.tr
              key={row.sending_account}
              custom={i}
              variants={tableRowVariants}
              initial="hidden"
              animate="visible"
              whileHover={{ backgroundColor: "rgba(238,242,255,0.6)" }}
              className="group border-b border-slate-50 transition-colors"
            >
              <td className="py-3.5 pr-4 font-semibold text-slate-800">{row.sending_account}</td>
              <td className="py-3.5 pr-4 text-right font-medium text-slate-700">{row.contacted}</td>
              <td className="py-3.5 pr-4 text-right font-medium text-slate-700">{row.opened}</td>
              <td className="py-3.5 text-right font-medium text-slate-700">{row.replied}</td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main view
// ---------------------------------------------------------------------------

export default function AnalyticsView() {
  const { workspace } = useWorkspace();
  const workspaceId = workspace?.workspace_id;

  const [activeTab, setActiveTab] = useState("campaign");
  const sectionRefs = useRef({ campaign: null, account: null });

  // Summary KPIs
  const [summary, setSummary] = useState({ total_sent: 0, open_rate: 0, click_rate: 0, reply_rate: 0 });

  // Graph
  const [chartData, setChartData] = useState([]);

  // Campaign analytics
  const [campaigns, setCampaigns] = useState([]);

  // Account performance
  const [selectedCampaignId, setSelectedCampaignId] = useState(null);
  const [accountRows, setAccountRows] = useState([]);

  const [loadError, setLoadError] = useState(null);
  const [accountLoadError, setAccountLoadError] = useState(null);
  const [isLoadingCore, setIsLoadingCore] = useState(false);
  const [isLoadingAccounts, setIsLoadingAccounts] = useState(false);

  const [filterCampaignId, setFilterCampaignId] = useState("");
  const [dateRangePreset, setDateRangePreset] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [filterMenuOpen, setFilterMenuOpen] = useState(false);
  const [rangeMenuOpen, setRangeMenuOpen] = useState(false);
  const [filterSearch, setFilterSearch] = useState("");
  const [rangeSearch, setRangeSearch] = useState("");
  const [calendarOpen, setCalendarOpen] = useState(false);
  const [customFromYmd, setCustomFromYmd] = useState(null);
  const [customToYmd, setCustomToYmd] = useState(null);
  const filterMenuRef = useRef(null);
  const rangeMenuRef = useRef(null);

  const reshapeGraph = useCallback((data) => {
    const gd = data?.graph_data;
    if (!gd || !Array.isArray(gd.labels) || !Array.isArray(gd.series)) {
      setChartData([]);
      return;
    }
    const { labels, series } = gd;
    const byKey = {};
    for (const s of series) {
      if (s?.key) byKey[s.key] = s.values;
    }
    const rows = labels.map((lbl, i) => ({
      label: lbl,
      total_sent: byKey.total_sent?.[i] ?? 0,
      open_rate: byKey.open_rate?.[i] ?? 0,
      click_rate: byKey.click_rate?.[i] ?? 0,
      reply_rate: byKey.reply_rate?.[i] ?? 0,
    }));
    setChartData(rows);
  }, []);

  useEffect(() => {
    setSelectedCampaignId(null);
    setAccountRows([]);
    setCampaigns([]);
    setChartData([]);
    setSummary({ total_sent: 0, open_rate: 0, click_rate: 0, reply_rate: 0 });
    setLoadError(null);
    setAccountLoadError(null);
    setFilterCampaignId("");
    setDateRangePreset("all");
    setStatusFilter("all");
    setFilterSearch("");
    setRangeSearch("");
    setCustomFromYmd(null);
    setCustomToYmd(null);
    setFilterMenuOpen(false);
    setRangeMenuOpen(false);
    setCalendarOpen(false);
  }, [workspaceId]);

  useEffect(() => {
    if (!filterMenuOpen && !rangeMenuOpen) return;
    function handleDown(event) {
      if (filterMenuOpen && filterMenuRef.current && !filterMenuRef.current.contains(event.target)) {
        setFilterMenuOpen(false);
      }
      if (rangeMenuOpen && rangeMenuRef.current && !rangeMenuRef.current.contains(event.target)) {
        setRangeMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleDown);
    return () => document.removeEventListener("mousedown", handleDown);
  }, [filterMenuOpen, rangeMenuOpen]);

  useEffect(() => {
    if (!workspaceId) return;

    let cancelled = false;
    const opts = { credentials: "include", headers: { Accept: "application/json" } };

    async function loadCore() {
      setIsLoadingCore(true);
      setLoadError(null);
      try {
        const summaryQs = buildSummaryQuery(
          filterCampaignId,
          dateRangePreset,
          customFromYmd,
          customToYmd,
          statusFilter
        );
        const graphQs = buildGraphQuery(
          filterCampaignId,
          dateRangePreset,
          customFromYmd,
          customToYmd,
          statusFilter
        );
        const summaryUrl = `${API}/workspaces/${workspaceId}/analytics/summary${summaryQs}`;
        const graphUrl = `${API}/workspaces/${workspaceId}/analytics/graph${graphQs}`;
        const campaignsUrl = `${API}/workspaces/${workspaceId}/analytics/campaigns`;

        const [sRes, gRes, cRes] = await Promise.all([
          fetch(summaryUrl, opts),
          fetch(graphUrl, opts),
          fetch(campaignsUrl, opts),
        ]);

        if (cancelled) return;

        if (!sRes.ok) {
          setLoadError(await readApiError(sRes));
          setChartData([]);
          setCampaigns([]);
          setIsLoadingCore(false);
          return;
        }
        if (!gRes.ok) {
          setLoadError(await readApiError(gRes));
          setChartData([]);
          setCampaigns([]);
          setIsLoadingCore(false);
          return;
        }
        if (!cRes.ok) {
          setLoadError(await readApiError(cRes));
          setChartData([]);
          setCampaigns([]);
          setIsLoadingCore(false);
          return;
        }

        const [summaryJson, graphJson, campaignsJson] = await Promise.all([
          sRes.json(),
          gRes.json(),
          cRes.json(),
        ]);

        if (cancelled) return;

        setSummary({
          total_sent: Number(summaryJson?.total_sent) || 0,
          open_rate: Number(summaryJson?.open_rate) || 0,
          click_rate: Number(summaryJson?.click_rate) || 0,
          reply_rate: Number(summaryJson?.reply_rate) || 0,
        });
        reshapeGraph(graphJson);

        const list = Array.isArray(campaignsJson?.campaigns) ? campaignsJson.campaigns : [];
        setCampaigns(list);
        setSelectedCampaignId((prev) => {
          if (list.length === 0) return null;
          if (filterCampaignId && list.some((c) => c.campaign_id === filterCampaignId)) {
            return filterCampaignId;
          }
          const stillValid = prev && list.some((c) => c.campaign_id === prev);
          return stillValid ? prev : list[0].campaign_id;
        });
      } catch {
        if (!cancelled) setLoadError("Network error while loading analytics.");
      } finally {
        if (!cancelled) setIsLoadingCore(false);
      }
    }

    loadCore();
    return () => {
      cancelled = true;
    };
  }, [
    workspaceId,
    filterCampaignId,
    dateRangePreset,
    customFromYmd,
    customToYmd,
    statusFilter,
    reshapeGraph,
  ]);

  useEffect(() => {
    if (!workspaceId || !selectedCampaignId) {
      setAccountRows([]);
      setAccountLoadError(null);
      return;
    }

    let cancelled = false;
    const opts = { credentials: "include", headers: { Accept: "application/json" } };

    async function loadAccounts() {
      setIsLoadingAccounts(true);
      setAccountLoadError(null);
      try {
        const url = `${API}/workspaces/${workspaceId}/analytics/account-performance?campaign_id=${encodeURIComponent(selectedCampaignId)}`;
        const res = await fetch(url, opts);
        if (cancelled) return;
        if (!res.ok) {
          setAccountLoadError(await readApiError(res));
          setAccountRows([]);
          return;
        }
        const data = await res.json();
        if (cancelled) return;
        setAccountRows(Array.isArray(data?.account_performance) ? data.account_performance : []);
      } catch {
        if (!cancelled) {
          setAccountLoadError("Network error while loading account performance.");
          setAccountRows([]);
        }
      } finally {
        if (!cancelled) setIsLoadingAccounts(false);
      }
    }

    loadAccounts();
    return () => {
      cancelled = true;
    };
  }, [workspaceId, selectedCampaignId]);

  function scrollToSection(key) {
    setActiveTab(key);
    sectionRefs.current[key]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const chartEmptyHint =
    loadError || isLoadingCore
      ? null
      : "No email events in this workspace for the selected period. Metrics come from sent mail and tracking (opens, clicks, replies) recorded in the database.";

  const displayedCampaigns = useMemo(() => {
    let rows = campaigns;
    rows = rows.filter((c) => matchesLifecycle(c.lifecycle, statusFilter));
    if (filterCampaignId) rows = rows.filter((c) => c.campaign_id === filterCampaignId);
    return rows;
  }, [campaigns, filterCampaignId, statusFilter]);

  const campaignsForFilterList = useMemo(() => {
    let rows = campaigns.filter((c) => matchesLifecycle(c.lifecycle, statusFilter));
    const q = filterSearch.trim().toLowerCase();
    if (q) rows = rows.filter((c) => (c.campaign_name || "").toLowerCase().includes(q));
    return rows;
  }, [campaigns, statusFilter, filterSearch]);

  const rangePresetRows = useMemo(() => {
    const q = rangeSearch.trim().toLowerCase();
    if (!q) return RANGE_PRESETS;
    return RANGE_PRESETS.filter((p) => p.label.toLowerCase().includes(q));
  }, [rangeSearch]);

  const filterSummaryLine = useMemo(() => {
    const preset = RANGE_PRESETS.find((p) => p.id === dateRangePreset)?.label ?? "All time";
    const camp = filterCampaignId
      ? campaigns.find((c) => c.campaign_id === filterCampaignId)?.campaign_name ?? "One campaign"
      : "All campaigns";
    const st = STATUS_FILTER_OPTIONS.find((s) => s.id === statusFilter)?.label ?? "All statuses";
    return `${preset} · ${st} · ${camp}`;
  }, [dateRangePreset, filterCampaignId, campaigns, statusFilter]);

  return (
    <section className="flex flex-1 flex-col gap-4 bg-slate-50/30 p-4 sm:p-6">
      {loadError ? (
        <div
          role="alert"
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
        >
          <p className="font-semibold">Analytics could not be loaded</p>
          <p className="mt-1 text-amber-800">{loadError}</p>
          <p className="mt-2 text-xs text-amber-700">
            Common causes: not signed in to the API origin (use the same browser session as login), missing{" "}
            <code className="rounded bg-amber-100/80 px-1">view_analytics</code> role, or the API URL in{" "}
            <code className="rounded bg-amber-100/80 px-1">NEXT_PUBLIC_API_BASE_URL</code> does not match where your session cookie was set.
          </p>
        </div>
      ) : null}

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex items-center gap-1 rounded-2xl bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => scrollToSection("campaign")}
              className={[
                "rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-200",
                activeTab === "campaign"
                  ? "bg-white text-indigo-600 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              ].join(" ")}
            >
              Campaign Analytics
            </button>
            <button
              type="button"
              onClick={() => scrollToSection("account")}
              className={[
                "rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-200",
                activeTab === "account"
                  ? "bg-white text-indigo-600 shadow-sm"
                  : "text-slate-500 hover:text-slate-700"
              ].join(" ")}
            >
              Account Analytics
            </button>
          </div>

          <div className="ml-auto inline-flex flex-wrap items-center justify-end gap-2">
            <div className="relative" ref={filterMenuRef}>
              <button
                type="button"
                aria-expanded={filterMenuOpen}
                aria-haspopup="true"
                onClick={() => {
                  setRangeMenuOpen(false);
                  setFilterMenuOpen((o) => !o);
                }}
                className={[
                  "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                  filterMenuOpen || statusFilter !== "all" || filterCampaignId
                    ? "border-blue-300 bg-blue-50 text-blue-800 hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-950/50 dark:text-blue-200"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
                ].join(" ")}
              >
                <Filter className="h-4 w-4 shrink-0" />
                Filter
                <ChevronDown
                  className={["h-4 w-4 shrink-0 transition-transform", filterMenuOpen ? "rotate-180" : ""].join(" ")}
                />
              </button>
              {filterMenuOpen ? (
                <div
                  role="dialog"
                  aria-label="Campaign and status filters"
                  className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900"
                >
                  <div className="px-3 pt-3">
                    <div className="relative">
                      <Search className="pointer-events-none absolute left-0 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <input
                        type="search"
                        placeholder="Search…"
                        value={filterSearch}
                        onChange={(e) => setFilterSearch(e.target.value)}
                        className="w-full border-0 border-b-2 border-blue-600 bg-transparent py-2 pl-7 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-blue-700 dark:text-slate-100 dark:placeholder:text-slate-500"
                      />
                    </div>
                  </div>
                  <div className="max-h-44 overflow-y-auto border-b border-slate-100 py-1 dark:border-slate-800">
                    <button
                      type="button"
                      onClick={() => setFilterCampaignId("")}
                      className={[
                        "flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800",
                        !filterCampaignId ? "font-semibold text-slate-900 dark:text-slate-100" : "text-slate-700 dark:text-slate-300",
                      ].join(" ")}
                    >
                      <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                        <Layers className="h-4 w-4" />
                      </span>
                      All campaigns
                    </button>
                    {campaignsForFilterList.map((c) => (
                      <button
                        key={c.campaign_id}
                        type="button"
                        onClick={() => {
                          setFilterCampaignId(c.campaign_id);
                          setFilterMenuOpen(false);
                        }}
                        className={[
                          "flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800",
                          filterCampaignId === c.campaign_id
                            ? "font-semibold text-slate-900 dark:text-slate-100"
                            : "text-slate-700 dark:text-slate-300",
                        ].join(" ")}
                      >
                        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                          {(c.campaign_name || "?").slice(0, 1).toUpperCase()}
                        </span>
                        <span className="truncate">{c.campaign_name}</span>
                      </button>
                    ))}
                  </div>
                  <p className="px-3 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                    Status
                  </p>
                  <div className="pb-2">
                    {STATUS_FILTER_OPTIONS.map(({ id, label, Icon }) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setStatusFilter(id)}
                        className={[
                          "flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800",
                          statusFilter === id
                            ? "font-semibold text-slate-900 dark:text-slate-100"
                            : "text-slate-700 dark:text-slate-300",
                        ].join(" ")}
                      >
                        <span
                          className={[
                            "flex h-8 w-8 items-center justify-center rounded-full",
                            id === "all"
                              ? "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400"
                              : null,
                            id === "active"
                              ? "bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400"
                              : null,
                            id === "paused"
                              ? "bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400"
                              : null,
                            id === "completed"
                              ? "bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400"
                              : null,
                          ]
                            .filter(Boolean)
                            .join(" ")}
                        >
                          <Icon className="h-4 w-4" />
                        </span>
                        {label}
                      </button>
                    ))}
                  </div>
                  <div className="flex justify-end gap-2 border-t border-slate-100 px-3 py-2 dark:border-slate-800">
                    <button
                      type="button"
                      className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                      onClick={() => {
                        setFilterCampaignId("");
                        setStatusFilter("all");
                        setFilterSearch("");
                      }}
                    >
                      Reset
                    </button>
                    <button
                      type="button"
                      className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-700"
                      onClick={() => setFilterMenuOpen(false)}
                    >
                      Done
                    </button>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="relative" ref={rangeMenuRef}>
              <button
                type="button"
                aria-expanded={rangeMenuOpen}
                aria-haspopup="true"
                onClick={() => {
                  setFilterMenuOpen(false);
                  setRangeMenuOpen((o) => !o);
                }}
                className={[
                  "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors",
                  rangeMenuOpen ||
                    dateRangePreset !== "all" ||
                    (dateRangePreset === "custom" && customFromYmd && customToYmd)
                    ? "border-blue-300 bg-blue-50 text-blue-800 hover:bg-blue-100 dark:border-blue-700 dark:bg-blue-950/50 dark:text-blue-200"
                    : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800",
                ].join(" ")}
              >
                <Calendar className="h-4 w-4 shrink-0" />
                {RANGE_PRESETS.find((p) => p.id === dateRangePreset)?.label ?? "Range"}
                <ChevronDown
                  className={["h-4 w-4 shrink-0 transition-transform", rangeMenuOpen ? "rotate-180" : ""].join(" ")}
                />
              </button>
              {rangeMenuOpen ? (
                <div
                  role="dialog"
                  aria-label="Date range"
                  className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900"
                >
                  <div className="px-3 pt-3">
                    <div className="relative">
                      <Search className="pointer-events-none absolute left-0 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                      <input
                        type="search"
                        placeholder="Search…"
                        value={rangeSearch}
                        onChange={(e) => setRangeSearch(e.target.value)}
                        className="w-full border-0 border-b-2 border-blue-600 bg-transparent py-2 pl-7 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-blue-700 dark:text-slate-100 dark:placeholder:text-slate-500"
                      />
                    </div>
                  </div>
                  <div className="max-h-64 overflow-y-auto py-1">
                    {rangePresetRows.map((p) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => {
                          if (p.id === "custom") {
                            setRangeMenuOpen(false);
                            setCalendarOpen(true);
                            return;
                          }
                          setDateRangePreset(p.id);
                          setCustomFromYmd(null);
                          setCustomToYmd(null);
                          setRangeMenuOpen(false);
                        }}
                        className={[
                          "flex w-full px-3 py-2.5 text-left text-sm hover:bg-slate-50 dark:hover:bg-slate-800",
                          dateRangePreset === p.id ||
                            (p.id === "custom" &&
                              dateRangePreset === "custom" &&
                              customFromYmd &&
                              customToYmd)
                            ? "font-semibold text-slate-900 dark:text-slate-100"
                            : "text-slate-700 dark:text-slate-300",
                        ].join(" ")}
                      >
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <p className="text-xs font-medium text-slate-500 dark:text-slate-400">{filterSummaryLine}</p>

      <motion.div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
        initial="hidden"
        animate="visible"
        variants={{ visible: { transition: { staggerChildren: 0.1, delayChildren: 0.05 } } }}
      >
        <KpiCard
          icon={Send}
          iconBg="bg-amber-50"
          toneClass="text-amber-500"
          bgClass="bg-gradient-to-br from-white to-amber-50/60"
          title="Total Sent"
          value={isLoadingCore && !loadError ? "…" : summary.total_sent.toLocaleString()}
        />
        <KpiCard
          icon={Mail}
          iconBg="bg-sky-50"
          toneClass="text-sky-500"
          bgClass="bg-gradient-to-br from-white to-sky-50/60"
          title="Open Rate"
          value={isLoadingCore && !loadError ? "…" : `${summary.open_rate}%`}
        />
        <KpiCard
          icon={MousePointerClick}
          iconBg="bg-emerald-50"
          toneClass="text-emerald-500"
          bgClass="bg-gradient-to-br from-white to-emerald-50/60"
          title="Click Rate"
          value={isLoadingCore && !loadError ? "…" : `${summary.click_rate}%`}
        />
        <KpiCard
          icon={MessageCircle}
          iconBg="bg-violet-50"
          toneClass="text-violet-500"
          bgClass="bg-gradient-to-br from-white to-violet-50/60"
          title="Reply Rate"
          value={isLoadingCore && !loadError ? "…" : `${summary.reply_rate}%`}
        />
      </motion.div>

      <AnalyticsChartCard chartData={chartData} emptyHint={chartEmptyHint} />

      <motion.div
        ref={(el) => { sectionRefs.current.campaign = el; }}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        className="rounded-2xl border border-slate-200/60 bg-white p-5 shadow-sm sm:p-6"
      >
        <div className="flex items-center gap-3 border-b border-slate-100 pb-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50">
            <Layers className="h-4 w-4 text-indigo-500" />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-indigo-500">Analytics</p>
              <h3 className="text-xl font-black tracking-tight text-slate-900">Campaign Performance</h3>
          </div>
        </div>
        <CampaignAnalyticsTable campaigns={displayedCampaigns} />
      </motion.div>

      <motion.div
        ref={(el) => { sectionRefs.current.account = el; }}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
        className="rounded-2xl border border-slate-200/60 bg-white p-5 shadow-sm sm:p-6"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-sky-50">
              <Mail className="h-4 w-4 text-sky-500" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-sky-500">Breakdown</p>
                <h3 className="text-xl font-black tracking-tight text-slate-900">Account Performance</h3>
            </div>
          </div>
          {(filterCampaignId ? displayedCampaigns : campaigns).length > 0 && (
            <select
              value={selectedCampaignId || ""}
              onChange={(e) => setSelectedCampaignId(e.target.value)}
              disabled={isLoadingAccounts}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 outline-none transition-all focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/20 disabled:opacity-60"
            >
              {(filterCampaignId ? displayedCampaigns : campaigns).map((c) => (
                <option key={c.campaign_id} value={c.campaign_id}>
                  {c.campaign_name}
                </option>
              ))}
            </select>
          )}
        </div>
        {isLoadingAccounts && !loadError ? (
          <div className="mt-5 flex items-center gap-2 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
            Loading account breakdown…
          </div>
        ) : null}
        {accountLoadError ? (
          <p className="mt-3 text-sm text-amber-800" role="alert">{accountLoadError}</p>
        ) : null}
        <AccountPerformanceTable rows={accountRows} />
      </motion.div>

      <AnalyticsDateRangeCalendar
        open={calendarOpen}
        onClose={() => setCalendarOpen(false)}
        initialFrom={customFromYmd}
        initialTo={customToYmd}
        onApply={({ from, to }) => {
          setCustomFromYmd(from);
          setCustomToYmd(to);
          setDateRangePreset("custom");
        }}
      />
    </section>
  );
}
