"use client";

import { useMemo, useRef, useState } from "react";
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

const seriesMeta = [
  { key: "sent", label: "Sent", tone: "text-amber-500" },
  { key: "totalOpens", label: "Total opens", tone: "text-sky-500" },
  { key: "uniqueOpens", label: "Unique opens", tone: "text-blue-700" },
  { key: "totalReplies", label: "Total replies", tone: "text-fuchsia-600" },
  { key: "totalClicks", label: "Total clicks", tone: "text-slate-900" },
  { key: "uniqueClicks", label: "Unique clicks", tone: "text-emerald-500" }
];

const analyticsData = [
  { date: "Mar 24", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 },
  { date: "Mar 28", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 },
  { date: "Apr 01", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 },
  { date: "Apr 05", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 },
  { date: "Apr 09", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 },
  { date: "Apr 13", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 },
  { date: "Apr 17", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 },
  { date: "Apr 21", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 },
  { date: "Apr 24", sent: 0, totalOpens: 0, uniqueOpens: 0, totalReplies: 0, totalClicks: 0, uniqueClicks: 0 }
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

function AnalyticsChartCard() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <ChartLegend />
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={analyticsData} margin={{ top: 16, right: 8, left: -20, bottom: 8 }}>
            <XAxis dataKey="date" tickLine={false} axisLine={{ stroke: "rgb(203 213 225)" }} tick={{ fill: "rgb(100 116 139)", fontSize: 11 }} />
            <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "rgb(148 163 184)", fontSize: 11 }} domain={[0, 1]} tickFormatter={() => "0"} />
            <Tooltip
              content={<AnalyticsTooltip />}
              cursor={{ stroke: "rgb(148 163 184)", strokeDasharray: "4 4" }}
            />

            <Area type="monotone" dataKey="sent" fill="rgb(245 158 11 / 0.12)" stroke="none" isAnimationActive />

            <Line type="monotone" dataKey="sent" stroke="currentColor" className="text-amber-500" strokeWidth={2} dot={false} isAnimationActive />
            <Line type="monotone" dataKey="totalOpens" stroke="currentColor" className="text-sky-500" strokeWidth={2} dot={false} isAnimationActive />
            <Line type="monotone" dataKey="uniqueOpens" stroke="currentColor" className="text-blue-700" strokeWidth={2} dot={false} isAnimationActive />
            <Line type="monotone" dataKey="totalReplies" stroke="currentColor" className="text-fuchsia-600" strokeWidth={2} dot={false} isAnimationActive />
            <Line type="monotone" dataKey="totalClicks" stroke="currentColor" className="text-slate-900" strokeWidth={2} dot={false} isAnimationActive />
            <Line type="monotone" dataKey="uniqueClicks" stroke="currentColor" className="text-emerald-500" strokeWidth={2} dot={false} isAnimationActive />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default function AnalyticsView() {
  const [activeTab, setActiveTab] = useState("campaign");
  const sectionRefs = useRef({ campaign: null, account: null });

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
                className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
              >
                <Calendar className="h-4 w-4" />
                Last 4 weeks
                <ChevronDown className="h-4 w-4" />
              </button>
            </div>
          </div>

        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard icon={Send} toneClass="text-amber-500" title="Total Sent" value="0" />
          <KpiCard icon={Mail} toneClass="text-sky-500" title="Open rate" value="0" />
          <KpiCard icon={MousePointerClick} toneClass="text-slate-900" title="Click rate" value="0" />
          <KpiCard icon={MessageCircle} toneClass="text-fuchsia-600" title="Reply rate" value="0" />
        </div>

        <AnalyticsChartCard />

          <div ref={(element) => {
          sectionRefs.current.campaign = element;
        }} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <div className="inline-flex rounded-lg bg-blue-50 px-3 py-1.5 text-sm font-semibold text-blue-600">
            Campaign Analytics
          </div>
          <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center">
            <p className="text-sm font-medium text-slate-600">👋 Your published campaigns will appear here</p>
          </div>
        </div>

        <div ref={(element) => {
          sectionRefs.current.account = element;
        }} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <h3 className="text-base font-semibold text-slate-900">Account performance</h3>
          <div className="mt-4 rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-12 text-center">
            <p className="text-sm font-medium text-slate-600">No data to display</p>
          </div>
        </div>
    </section>
  );
}