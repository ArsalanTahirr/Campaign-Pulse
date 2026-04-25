"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  MoreHorizontal,
  Pause,
  Play,
  Search,
  Zap
} from "lucide-react";

const statusOptions = [
  { label: "All statuses", value: "all", icon: Zap, iconClass: "text-slate-500" },
  { label: "Active", value: "active", icon: Play, iconClass: "text-blue-600" },
  { label: "Paused", value: "paused", icon: Pause, iconClass: "text-amber-500" },
  { label: "Error", value: "error", icon: AlertTriangle, iconClass: "text-rose-500" },
  { label: "Completed", value: "completed", icon: CheckCircle2, iconClass: "text-emerald-600" }
];

const sortOptions = [
  { label: "Newest first", value: "newest" },
  { label: "Oldest first", value: "oldest" },
  { label: "Name A-Z", value: "name-asc" },
  { label: "Name Z-A", value: "name-desc" }
];

const statusBadgeClasses = {
  active: "bg-blue-600 text-white",
  completed: "bg-emerald-600 text-white",
  draft: "bg-slate-200 text-slate-700",
  paused: "bg-amber-500 text-white",
  error: "bg-rose-500 text-white",
  evergreen: "bg-sky-600 text-white"
};

function toTitleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function CampaignsView() {
  const [campaigns] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isStatusOpen, setIsStatusOpen] = useState(false);
  const [isSortOpen, setIsSortOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState(statusOptions[0]);
  const [selectedSort, setSelectedSort] = useState(sortOptions[0]);
  const statusRef = useRef(null);
  const sortRef = useRef(null);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (statusRef.current && !statusRef.current.contains(event.target)) {
        setIsStatusOpen(false);
      }
      if (sortRef.current && !sortRef.current.contains(event.target)) {
        setIsSortOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  const hasCampaignRecords = campaigns.length > 0;

  const filteredCampaigns = useMemo(() => {
    if (!hasCampaignRecords) {
      return [];
    }

    const normalizedSearch = searchTerm.trim().toLowerCase();

    const baseList = campaigns.filter((campaign) => {
      const statusMatch =
        selectedStatus.value === "all" || campaign.status === selectedStatus.value;
      const nameMatch = campaign.name.toLowerCase().includes(normalizedSearch);
      return statusMatch && nameMatch;
    });

    const sorted = [...baseList];

    if (selectedSort.value === "newest") {
      sorted.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    }
    if (selectedSort.value === "oldest") {
      sorted.sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
    }
    if (selectedSort.value === "name-asc") {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    }
    if (selectedSort.value === "name-desc") {
      sorted.sort((a, b) => b.name.localeCompare(a.name));
    }

    return sorted;
  }, [campaigns, hasCampaignRecords, searchTerm, selectedSort.value, selectedStatus.value]);

  const isEmpty = !hasCampaignRecords;
  const SelectedStatusIcon = selectedStatus.icon;

  return (
    <section className="flex flex-1 flex-col gap-5 bg-slate-50/60 px-6 py-6 sm:px-8">
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div className="relative w-full lg:max-w-md">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search..."
            className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-300"
          />
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <div className="relative" ref={statusRef}>
            <button
              type="button"
              onClick={() => {
                setIsStatusOpen((prev) => !prev);
                setIsSortOpen(false);
              }}
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition-all hover:border-slate-300 hover:bg-slate-50"
            >
              <SelectedStatusIcon className={["h-4 w-4", selectedStatus.iconClass].join(" ")} />
              <span>{selectedStatus.label}</span>
              <ChevronDown
                className={[
                  "h-4 w-4 text-slate-500 transition-transform",
                  isStatusOpen ? "rotate-180" : ""
                ].join(" ")}
              />
            </button>

            {isStatusOpen ? (
              <div className="absolute right-0 top-11 z-20 w-52 rounded-xl border border-slate-200 bg-white p-1 shadow-lg">
                {statusOptions.map((option) => {
                  const Icon = option.icon;
                  const isSelected = selectedStatus.value === option.value;

                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setSelectedStatus(option);
                        setIsStatusOpen(false);
                      }}
                      className={[
                        "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                        isSelected
                          ? "bg-sky-50 text-sky-700"
                          : "text-slate-700 hover:bg-slate-50"
                      ].join(" ")}
                    >
                      <Icon className={["h-4 w-4", option.iconClass].join(" ")} />
                      {option.label}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>

          <div className="relative" ref={sortRef}>
            <button
              type="button"
              onClick={() => {
                setIsSortOpen((prev) => !prev);
                setIsStatusOpen(false);
              }}
              className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 transition-all hover:border-slate-300 hover:bg-slate-50"
            >
              <span>{selectedSort.label}</span>
              <ChevronDown
                className={[
                  "h-4 w-4 text-slate-500 transition-transform",
                  isSortOpen ? "rotate-180" : ""
                ].join(" ")}
              />
            </button>

            {isSortOpen ? (
              <div className="absolute right-0 top-11 z-20 w-44 rounded-xl border border-slate-200 bg-white p-1 shadow-lg">
                {sortOptions.map((option) => {
                  const isSelected = selectedSort.value === option.value;

                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => {
                        setSelectedSort(option);
                        setIsSortOpen(false);
                      }}
                      className={[
                        "w-full rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                        isSelected
                          ? "bg-sky-50 text-sky-700"
                          : "text-slate-700 hover:bg-slate-50"
                      ].join(" ")}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>

          <button
            type="button"
            className="inline-flex h-10 items-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm transition-all hover:bg-blue-700"
          >
            + Add New
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50/40 p-3">
        <div className="min-w-[1080px]">
          <div className="mb-2 grid grid-cols-[36px_minmax(210px,1.3fr)_130px_150px_80px_80px_90px_140px_80px] items-center px-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
            <div>
              <input type="checkbox" className="h-4 w-4 rounded border-slate-300" />
            </div>
            <div>Name</div>
            <div>Status</div>
            <div>Progress</div>
            <div>Sent</div>
            <div>Click</div>
            <div>Replied</div>
            <div>Opportunities</div>
            <div />
          </div>

          {isEmpty ? (
            <div className="py-20 flex flex-col items-center justify-center text-center">
              <Image
                src="/campaignDood.png"
                alt="Campaigns empty state"
                width={500}
                height={500}
                className="h-auto w-full max-w-[340px] mix-blend-multiply opacity-60"
                priority
              />
              <p className="mt-3 text-lg font-semibold text-slate-800">
                Add a campaign to start sending emails
              </p>
              <button
                type="button"
                className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-blue-700"
              >
                + Add New
              </button>
            </div>
          ) : (
            filteredCampaigns.map((campaign) => (
              <div
                key={campaign.id}
                className="mb-3 grid grid-cols-[36px_minmax(210px,1.3fr)_130px_150px_80px_80px_90px_140px_80px] items-center rounded-xl border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700 shadow-sm"
              >
                <div>
                  <input type="checkbox" className="h-4 w-4 rounded border-slate-300" />
                </div>

                <div className="font-semibold text-slate-800">{campaign.name}</div>

                <div>
                  <span
                    className={[
                      "inline-flex rounded-full px-2.5 py-1 text-xs font-semibold",
                      statusBadgeClasses[campaign.status] || "bg-slate-200 text-slate-700"
                    ].join(" ")}
                  >
                    {toTitleCase(campaign.status)}
                  </span>
                </div>

                <div>
                  <p className="text-sm font-medium text-slate-700">{campaign.progress}%</p>
                  <div className="mt-1 h-1.5 w-24 rounded-full bg-slate-200">
                    <div
                      className="h-1.5 rounded-full bg-emerald-500"
                      style={{ width: `${Math.min(campaign.progress, 100)}%` }}
                    />
                  </div>
                </div>

                <div>{campaign.sent}</div>
                <div>{campaign.click}</div>
                <div>{campaign.replied}</div>
                <div>{campaign.opportunities}</div>

                <div className="ml-auto flex items-center gap-1">
                  <button
                    type="button"
                    className="rounded-md p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
                    aria-label="Pause campaign"
                  >
                    <Pause className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    className="rounded-md p-1.5 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
                    aria-label="More options"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
