"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
  ChevronDown,
  Filter,
  Info,
  Link2,
  Mail,
  MessageCircle,
  MousePointerClick,
  Send
} from "lucide-react";
import { useWorkspace } from "@/contexts/WorkspaceContext";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// Exactly 4 series as required.
const seriesMeta = [
  { key: "total_sent", label: "Total Emails Sent", tone: "text-amber-500" },
  { key: "open_rate",  label: "Open Rate (%)",     tone: "text-sky-500"   },
  { key: "click_rate", label: "Click Rate (%)",    tone: "text-emerald-500"},
  { key: "reply_rate", label: "Reply Rate (%)",    tone: "text-fuchsia-600"},
];

const metricByKey = seriesMeta.reduce((acc, item) => {
  acc[item.key] = item;
  return acc;
}, {});

function KpiCard({ icon: Icon, toneClass, title, value, subValue }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className={["inline-flex items-center gap-2", toneClass].join(" ")}>
          <Icon className="h-4 w-4" />
          <span className="text-xs font-semibold uppercase tracking-wide">{title}</span>
        </div>
        <Info className="h-3.5 w-3.5 text-slate-400" />
      </div>
      <p className="mt-3 text-2xl font-semibold text-slate-900">{value}</p>
      {subValue ? <p className="text-xs font-medium text-slate-500">{subValue}</p> : null}
    </div>
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

function AnalyticsChartCard({ chartData }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <ChartLegend />
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
            <Line yAxisId="left"  type="monotone" dataKey="total_sent"  stroke="#f59e0b" strokeWidth={2} dot={false} isAnimationActive />
            <Line yAxisId="right" type="monotone" dataKey="open_rate"   stroke="#0ea5e9" strokeWidth={2} dot={false} isAnimationActive />
            <Line yAxisId="right" type="monotone" dataKey="click_rate"  stroke="#10b981" strokeWidth={2} dot={false} isAnimationActive />
            <Line yAxisId="right" type="monotone" dataKey="reply_rate"  stroke="#c026d3" strokeWidth={2} dot={false} isAnimationActive />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Campaign analytics table
// ---------------------------------------------------------------------------

function CampaignAnalyticsTable({ campaigns }) {
  if (!campaigns || campaigns.length === 0) {
    return (
      <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center">
        <p className="text-sm font-medium text-slate-600">No campaign data available</p>
      </div>
    );
  }

  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <th className="py-2 pr-4 text-left">Campaign</th>
            <th className="py-2 pr-4 text-left">Status</th>
            <th className="py-2 pr-4 text-right">Sequence Started</th>
            <th className="py-2 pr-4 text-right">Opened</th>
            <th className="py-2 pr-4 text-right">Replied</th>
            <th className="py-2 text-right">Opportunities</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((row) => (
            <tr key={row.campaign_id} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 pr-4 font-medium text-slate-800">{row.campaign_name}</td>
              <td className="py-3 pr-4">
                <span className={[
                  "inline-flex rounded-full px-2 py-0.5 text-xs font-semibold",
                  row.status === "active"
                    ? "bg-green-50 text-green-700"
                    : "bg-slate-100 text-slate-600"
                ].join(" ")}>
                  {row.status}
                </span>
              </td>
              <td className="py-3 pr-4 text-right text-slate-700">{row.sequence_started}</td>
              <td className="py-3 pr-4 text-right text-slate-700">{row.opened}</td>
              <td className="py-3 pr-4 text-right text-slate-700">
                {row.replied.count}
                <span className="ml-1 text-xs text-slate-400">({row.replied.rate}%)</span>
              </td>
              <td className="py-3 text-right text-slate-700">{row.opportunities}</td>
            </tr>
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
      <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center">
        <p className="text-sm font-medium text-slate-600">No account data for this campaign</p>
      </div>
    );
  }

  return (
    <div className="mt-4 overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <th className="py-2 pr-4 text-left">Sending Account</th>
            <th className="py-2 pr-4 text-right">Contacted</th>
            <th className="py-2 pr-4 text-right">Opened</th>
            <th className="py-2 text-right">Replied</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.sending_account} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-3 pr-4 font-medium text-slate-800">{row.sending_account}</td>
              <td className="py-3 pr-4 text-right text-slate-700">{row.contacted}</td>
              <td className="py-3 pr-4 text-right text-slate-700">{row.opened}</td>
              <td className="py-3 text-right text-slate-700">{row.replied}</td>
            </tr>
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
  const [granularity, setGranularity] = useState("daily");
  const [chartData, setChartData] = useState([]);

  // Campaign analytics
  const [campaigns, setCampaigns] = useState([]);

  // Account performance
  const [selectedCampaignId, setSelectedCampaignId] = useState(null);
  const [accountRows, setAccountRows] = useState([]);

  // Fetch summary
  useEffect(() => {
    if (!workspaceId) return;
    fetch(`${API}/workspaces/${workspaceId}/analytics/summary`, { credentials: "include" })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data) setSummary(data); })
      .catch(() => {});
  }, [workspaceId]);

  // Fetch graph
  useEffect(() => {
    if (!workspaceId) return;
    fetch(`${API}/workspaces/${workspaceId}/analytics/graph?granularity=${granularity}`, { credentials: "include" })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data) return;
        const { labels, series } = data.graph_data;
        // Reshape from series arrays into per-label objects for Recharts
        const byKey = {};
        for (const s of series) {
          byKey[s.key] = s.values;
        }
        const rows = labels.map((lbl, i) => ({
          label: lbl,
          total_sent:  byKey.total_sent?.[i]  ?? 0,
          open_rate:   byKey.open_rate?.[i]   ?? 0,
          click_rate:  byKey.click_rate?.[i]  ?? 0,
          reply_rate:  byKey.reply_rate?.[i]  ?? 0,
        }));
        setChartData(rows);
      })
      .catch(() => {});
  }, [workspaceId, granularity]);

  // Fetch campaign analytics
  useEffect(() => {
    if (!workspaceId) return;
    fetch(`${API}/workspaces/${workspaceId}/analytics/campaigns`, { credentials: "include" })
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (!data) return;
        setCampaigns(data.campaigns);
        // Auto-select first campaign for account performance
        if (data.campaigns.length > 0 && !selectedCampaignId) {
          setSelectedCampaignId(data.campaigns[0].campaign_id);
        }
      })
      .catch(() => {});
  // selectedCampaignId intentionally excluded — only set on first load
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId]);

  // Fetch account performance when selected campaign changes
  useEffect(() => {
    if (!workspaceId || !selectedCampaignId) return;
    fetch(
      `${API}/workspaces/${workspaceId}/analytics/account-performance?campaign_id=${selectedCampaignId}`,
      { credentials: "include" }
    )
      .then((r) => r.ok ? r.json() : null)
      .then((data) => { if (data) setAccountRows(data.account_performance); })
      .catch(() => {});
  }, [workspaceId, selectedCampaignId]);

  const activeTabLabel = useMemo(
    () => (activeTab === "campaign" ? "Campaign Analytics" : "Account Analytics"),
    [activeTab]
  );

  function scrollToSection(key) {
    setActiveTab(key);
    sectionRefs.current[key]?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <section className="flex flex-1 flex-col gap-4 bg-slate-50/60 p-4 sm:p-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white p-1">
            <button
              type="button"
              onClick={() => scrollToSection("campaign")}
              className={[
                "rounded-md px-3 py-1.5 text-sm font-semibold transition-colors",
                activeTab === "campaign" ? "bg-blue-50 text-blue-600" : "text-slate-600 hover:bg-slate-100"
              ].join(" ")}
            >
              Campaign Analytics
            </button>
            <button
              type="button"
              onClick={() => scrollToSection("account")}
              className={[
                "rounded-md px-3 py-1.5 text-sm font-semibold transition-colors",
                activeTab === "account" ? "bg-blue-50 text-blue-600" : "text-slate-600 hover:bg-slate-100"
              ].join(" ")}
            >
              Account Analytics
            </button>
          </div>

          <div className="ml-auto inline-flex flex-wrap items-center justify-end gap-2">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              <Link2 className="h-4 w-4" />
              Share
            </button>
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              <Filter className="h-4 w-4" />
              Filter
              <ChevronDown className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => {
                const order = ["daily", "weekly", "monthly"];
                setGranularity((prev) => order[(order.indexOf(prev) + 1) % order.length]);
              }}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              <Calendar className="h-4 w-4" />
              {granularity.charAt(0).toUpperCase() + granularity.slice(1)}
              <ChevronDown className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard icon={Send}             toneClass="text-amber-500"   title="Total Sent"  value={summary.total_sent.toLocaleString()} />
        <KpiCard icon={Mail}             toneClass="text-sky-500"     title="Open Rate"   value={`${summary.open_rate}%`} />
        <KpiCard icon={MousePointerClick} toneClass="text-emerald-500" title="Click Rate"  value={`${summary.click_rate}%`} />
        <KpiCard icon={MessageCircle}    toneClass="text-fuchsia-600" title="Reply Rate"  value={`${summary.reply_rate}%`} />
      </div>

      <AnalyticsChartCard chartData={chartData} />

      <div
        ref={(el) => { sectionRefs.current.campaign = el; }}
        className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
      >
        <div className="inline-flex rounded-lg bg-blue-50 px-3 py-1.5 text-sm font-semibold text-blue-600">
          Campaign Analytics
        </div>
        <CampaignAnalyticsTable campaigns={campaigns} />
      </div>

      <div
        ref={(el) => { sectionRefs.current.account = el; }}
        className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-base font-semibold text-slate-900">Account performance</h3>
          {campaigns.length > 0 && (
            <select
              value={selectedCampaignId || ""}
              onChange={(e) => setSelectedCampaignId(e.target.value)}
              className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {campaigns.map((c) => (
                <option key={c.campaign_id} value={c.campaign_id}>
                  {c.campaign_name}
                </option>
              ))}
            </select>
          )}
        </div>
        <AccountPerformanceTable rows={accountRows} />
      </div>
    </section>
  );
}
