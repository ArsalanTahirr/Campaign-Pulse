"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bolt,
  EllipsisVertical,
  ChevronDown,
  Clock3,
  Inbox,
  MailOpen,
  Search,
  Send,
  CalendarClock,
  BellRing
} from "lucide-react";

const pipelineStatuses = [
  { id: "lead", label: "Lead", iconClass: "text-slate-400" },
  { id: "interested", label: "Interested", iconClass: "text-emerald-500" },
  { id: "meeting-booked", label: "Meeting booked", iconClass: "text-brand-600" },
  { id: "meeting-completed", label: "Meeting completed", iconClass: "text-amber-500" },
  { id: "won", label: "Won", iconClass: "text-lime-500" }
];

const campaignItems = [
//   { id: "spring-launch", label: "Spring Launch" },
//   { id: "re-engage-q2", label: "Re-engage Q2" },
//   { id: "winback-enterprise", label: "Winback Enterprise" }
];

const inboxItems = [
//   { id: "sales-primary", label: "Sales Inbox" },
//   { id: "team-shared", label: "Team Shared" },
//   { id: "founder", label: "Founder" }
];

const moreOptions = [
  { id: "inbox", label: "Inbox", icon: Inbox },
  { id: "unread-only", label: "Unread only", icon: MailOpen },
  { id: "reminders-only", label: "Reminders only", icon: BellRing },
  { id: "scheduled", label: "Scheduled emails", icon: CalendarClock },
  { id: "sent", label: "Sent", icon: Send }
];

const uniboxRecords = {
  "pipeline:lead": [
    {
      id: "lead-1",
      contact: "Ava Johnson",
      subject: "Intro call for rollout planning",
      meta: "2m ago"
    },
    {
      id: "lead-2",
      contact: "Liam Chen",
      subject: "Follow up on pricing deck",
      meta: "11m ago"
    }
  ],
  "pipeline:interested": [
    {
      id: "int-1",
      contact: "Sophia Patel",
      subject: "Requested security questionnaire",
      meta: "35m ago"
    }
  ],
  "pipeline:meeting-booked": [
    {
      id: "meet-1",
      contact: "Noah Silva",
      subject: "Demo confirmed for next Tuesday",
      meta: "1h ago"
    }
  ],
  "pipeline:meeting-completed": [],
  "pipeline:won": [
    {
      id: "lost-1",
      contact: "Mia Turner",
      subject: "Paused due to internal budgeting",
      meta: "Yesterday"
    }
  ],
  "campaign:spring-launch": [
    {
      id: "camp-1",
      contact: "Nora Hall",
      subject: "Question about launch timeline",
      meta: "8m ago"
    }
  ],
  "campaign:re-engage-q2": [
    {
      id: "camp-2",
      contact: "Ethan Miles",
      subject: "Can we restart the sequence?",
      meta: "44m ago"
    }
  ],
  "campaign:winback-enterprise": [],
  "inbox:sales-primary": [
    {
      id: "ibox-1",
      contact: "Olivia Green",
      subject: "Contract redlines attached",
      meta: "Just now"
    },
    {
      id: "ibox-2",
      contact: "Lucas Reed",
      subject: "Shared internal stakeholder notes",
      meta: "19m ago"
    }
  ],
  "inbox:team-shared": [
    {
      id: "ibox-3",
      contact: "Grace Ward",
      subject: "Need a revised onboarding proposal",
      meta: "1h ago"
    }
  ],
  "inbox:founder": [],
  "more:inbox": [
    {
      id: "more-1",
      contact: "Inbox overview",
      subject: "All conversations across connected inboxes",
      meta: "Live"
    }
  ],
  "more:unread-only": [],
  "more:reminders-only": [],
  "more:scheduled": [
    {
      id: "more-2",
      contact: "2 scheduled",
      subject: "Upcoming sends for today",
      meta: "Today"
    }
  ],
  "more:sent": [
    {
      id: "more-3",
      contact: "Sent activity",
      subject: "Recent sent emails from all teammates",
      meta: "Updated"
    }
  ]
};

function EmptyState({ heading }) {
  return (
    <div className="flex h-full min-h-[360px] flex-col items-center justify-center rounded-2xl border border-slate-200 bg-white/70 p-8 text-center">
      <Image
        src="/unibox-doodle.png"
        alt="unibox-doodle"
        width={580}
        height={580}
        className="h-auto w-full max-w-[260px] mix-blend-multiply opacity-75"
        priority
      />
      <p className="mt-3 text-sm font-medium text-slate-500">{heading}</p>
      <p className="mt-1 text-base font-semibold text-slate-800">
        No data is available for this view right now.
      </p>
    </div>
  );
}

function selectionTitle(selection) {
  if (selection.type === "pipeline") {
    return pipelineStatuses.find((item) => item.id === selection.id)?.label || "Pipeline";
  }
  if (selection.type === "status-more") {
    return "More";
  }
  if (selection.type === "campaign") {
    return campaignItems.find((item) => item.id === selection.id)?.label || "Campaign";
  }
  if (selection.type === "inbox") {
    return inboxItems.find((item) => item.id === selection.id)?.label || "Inbox";
  }
  return moreOptions.find((item) => item.id === selection.id)?.label || "More";
}

export default function UniboxView() {
  const [activeSelection, setActiveSelection] = useState({
    type: "pipeline",
    id: "lead"
  });
  const [isStatusOpen, setIsStatusOpen] = useState(true);
  const [isCampaignsOpen, setIsCampaignsOpen] = useState(false);
  const [isInboxesOpen, setIsInboxesOpen] = useState(false);
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const [statusSearch, setStatusSearch] = useState("");
  const [campaignSearch, setCampaignSearch] = useState("");
  const [inboxSearch, setInboxSearch] = useState("");

  const filteredStatuses = useMemo(() => {
    const query = statusSearch.trim().toLowerCase();
    if (!query) {
      return pipelineStatuses;
    }
    return pipelineStatuses.filter((status) =>
      status.label.toLowerCase().includes(query)
    );
  }, [statusSearch]);

  const filteredCampaigns = useMemo(() => {
    const query = campaignSearch.trim().toLowerCase();
    if (!query) {
      return campaignItems;
    }
    return campaignItems.filter((campaign) =>
      campaign.label.toLowerCase().includes(query)
    );
  }, [campaignSearch]);

  const filteredInboxes = useMemo(() => {
    const query = inboxSearch.trim().toLowerCase();
    if (!query) {
      return inboxItems;
    }
    return inboxItems.filter((inbox) => inbox.label.toLowerCase().includes(query));
  }, [inboxSearch]);

  const activeKey = `${activeSelection.type}:${activeSelection.id}`;
  const activeRecords = uniboxRecords[activeKey] || [];
  const activeLabel = selectionTitle(activeSelection);

  return (
    <section className="flex flex-1 bg-slate-50/60 p-4 sm:p-6">
      <div className="flex w-full flex-col gap-4 lg:flex-row">
        <aside className="w-full rounded-2xl border border-slate-200 bg-white p-4 shadow-sm lg:w-[340px] lg:shrink-0">
          <div>
            <button
              type="button"
              onClick={() => setIsStatusOpen((prev) => !prev)}
              className="flex w-full items-center justify-between rounded-xl bg-sky-50 px-3 py-2 text-left text-sm font-semibold text-slate-700 transition-colors hover:bg-sky-100"
            >
              <span>Status</span>
              <ChevronDown
                className={[
                  "h-4 w-4 text-slate-500 transition-transform duration-200",
                  isStatusOpen ? "rotate-180" : ""
                ].join(" ")}
              />
            </button>

            <AnimatePresence initial={false}>
              {isStatusOpen ? (
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
                      onChange={(event) => setStatusSearch(event.target.value)}
                      placeholder="Search status"
                      className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-300"
                    />
                  </div>

                  <div className="mt-2 space-y-1">
                    {filteredStatuses.length > 0 ? (
                      filteredStatuses.map((status) => {
                        const isActive =
                          activeSelection.type === "pipeline" && activeSelection.id === status.id;

                        return (
                          <button
                            key={status.id}
                            type="button"
                            onClick={() =>
                              setActiveSelection({
                                type: "pipeline",
                                id: status.id
                              })
                            }
                            className={[
                              "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors duration-200",
                              isActive
                                ? "bg-slate-100 text-slate-900"
                                : "text-slate-700 hover:bg-slate-100"
                            ].join(" ")}
                          >
                            <Bolt className={["h-4 w-4", status.iconClass].join(" ")} />
                            {status.label}
                          </button>
                        );
                      })
                    ) : (
                      <p className="rounded-lg px-3 py-2 text-xs text-slate-500">
                        No status found.
                      </p>
                    )}

                    <button
                      type="button"
                      onClick={() =>
                        setActiveSelection({
                          type: "status-more",
                          id: "more"
                        })
                      }
                      className={[
                        "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors duration-200",
                        activeSelection.type === "status-more"
                          ? "bg-slate-100 text-slate-900"
                          : "text-slate-700 hover:bg-slate-100"
                      ].join(" ")}
                    >
                      <EllipsisVertical className="h-4 w-4 text-slate-500" />
                      More
                    </button>
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

          <div className="mt-5 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={() => setIsCampaignsOpen((prev) => !prev)}
              className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"
            >
              <span>All Campaigns</span>
              <ChevronDown
                className={[
                  "h-4 w-4 text-slate-500 transition-transform",
                  isCampaignsOpen ? "rotate-180" : ""
                ].join(" ")}
              />
            </button>

            <AnimatePresence initial={false}>
              {isCampaignsOpen ? (
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
                      onChange={(event) => setCampaignSearch(event.target.value)}
                      placeholder="Search campaigns"
                      className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-300"
                    />
                  </div>

                  <div className="mt-2 space-y-1">
                    {filteredCampaigns.length > 0 ? (
                      filteredCampaigns.map((campaign) => {
                        const isActive =
                          activeSelection.type === "campaign" &&
                          activeSelection.id === campaign.id;

                        return (
                          <button
                            key={campaign.id}
                            type="button"
                            onClick={() =>
                              setActiveSelection({
                                type: "campaign",
                                id: campaign.id
                              })
                            }
                            className={[
                              "flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition-colors",
                              isActive
                                ? "bg-blue-50 text-blue-600"
                                : "text-slate-700 hover:bg-slate-50"
                            ].join(" ")}
                          >
                            {campaign.label}
                          </button>
                        );
                      })
                    ) : (
                      <p className="px-3 py-2 text-xs text-slate-500">No campaigns found.</p>
                    )}
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

          <div className="mt-4 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={() => setIsInboxesOpen((prev) => !prev)}
              className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"
            >
              <span>All Inboxes</span>
              <ChevronDown
                className={[
                  "h-4 w-4 text-slate-500 transition-transform",
                  isInboxesOpen ? "rotate-180" : ""
                ].join(" ")}
              />
            </button>

            <AnimatePresence initial={false}>
              {isInboxesOpen ? (
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
                      onChange={(event) => setInboxSearch(event.target.value)}
                      placeholder="Search inboxes"
                      className="h-10 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 outline-none transition-colors focus:border-blue-300"
                    />
                  </div>

                  <div className="mt-2 space-y-1">
                    {filteredInboxes.length > 0 ? (
                      filteredInboxes.map((inbox) => {
                        const isActive =
                          activeSelection.type === "inbox" && activeSelection.id === inbox.id;

                        return (
                          <button
                            key={inbox.id}
                            type="button"
                            onClick={() =>
                              setActiveSelection({
                                type: "inbox",
                                id: inbox.id
                              })
                            }
                            className={[
                              "flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition-colors",
                              isActive
                                ? "bg-blue-50 text-blue-600"
                                : "text-slate-700 hover:bg-slate-50"
                            ].join(" ")}
                          >
                            {inbox.label}
                          </button>
                        );
                      })
                    ) : (
                      <p className="px-3 py-2 text-xs text-slate-500">No inboxes found.</p>
                    )}
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

          <div className="mt-4 border-t border-slate-200 pt-4">
            <button
              type="button"
              onClick={() => setIsMoreOpen((prev) => !prev)}
              className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"
            >
              <span>More</span>
              <ChevronDown
                className={[
                  "h-4 w-4 text-slate-500 transition-transform",
                  isMoreOpen ? "rotate-180" : ""
                ].join(" ")}
              />
            </button>

            <AnimatePresence initial={false}>
              {isMoreOpen ? (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="mt-2 space-y-1">
                    {moreOptions.map((option) => {
                      const Icon = option.icon;
                      const isActive =
                        activeSelection.type === "more" && activeSelection.id === option.id;

                      return (
                        <button
                          key={option.id}
                          type="button"
                          onClick={() =>
                            setActiveSelection({
                              type: "more",
                              id: option.id
                            })
                          }
                          className={[
                            "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                            isActive
                              ? "bg-blue-50 text-blue-600"
                              : "text-slate-700 hover:bg-slate-50"
                          ].join(" ")}
                        >
                          <Icon className="h-4 w-4" />
                          {option.label}
                        </button>
                      );
                    })}
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>
        </aside>

        <div className="flex min-h-[420px] flex-1 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeKey}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="flex w-full flex-col"
            >
              <div className="flex items-center justify-between border-b border-slate-200 pb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Active View
                  </p>
                  <h2 className="text-xl font-semibold text-slate-900">{activeLabel}</h2>
                </div>
                <div className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600">
                  <Clock3 className="h-3.5 w-3.5" />
                  Live updates
                </div>
              </div>

              <div className="mt-4 flex-1">
                {activeRecords.length === 0 ? (
                  <EmptyState heading={activeLabel} />
                ) : (
                  <div className="space-y-3">
                    {activeRecords.map((record) => (
                      <div
                        key={record.id}
                        className="rounded-xl border border-slate-200 bg-slate-50/60 p-4"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-semibold text-slate-900">{record.contact}</p>
                            <p className="mt-1 text-sm text-slate-600">{record.subject}</p>
                          </div>
                          <span className="text-xs font-medium text-slate-500">{record.meta}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}