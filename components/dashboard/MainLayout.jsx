"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Plus, Search } from "lucide-react";
import { Space_Grotesk } from "next/font/google";
import Sidebar from "@/components/dashboard/Sidebar";
import CampaignsView from "@/components/dashboard/CampaignsView";
import EmailAccountsView from "@/components/dashboard/EmailAccountsView";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "700"]
});

const viewMeta = {
  email: { title: "Email Accounts" },
  campaigns: { title: "Campaigns" },
  unibox: { title: "Unibox" },
  analytics: { title: "Analytics" }
};

export default function MainLayout() {
  const [activeView, setActiveView] = useState("email");
  const [isOrgMenuOpen, setIsOrgMenuOpen] = useState(false);
  const [orgSearch, setOrgSearch] = useState("");
  const [selectedOrg, setSelectedOrg] = useState("My Organization");
  const orgMenuRef = useRef(null);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (orgMenuRef.current && !orgMenuRef.current.contains(event.target)) {
        setIsOrgMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);

    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  const activeTitle = useMemo(
    () => viewMeta[activeView]?.title || "Dashboard",
    [activeView]
  );

  return (
    <div className="flex min-h-screen bg-slate-50/60">
      <Sidebar activeView={activeView} onViewChange={setActiveView} />

      <main className="flex flex-1 flex-col">
        <header className="flex h-20 items-center justify-between border-b border-slate-200 bg-white px-6 sm:px-8">
          <h1
            className={[
              spaceGrotesk.className,
              "text-xl font-semibold tracking-tight text-slate-800 transition-all duration-300 sm:text-2xl",
              activeView === "email"
                ? "cursor-default bg-gradient-to-r from-sky-600 via-blue-600 to-cyan-500 bg-[length:200%_100%] bg-clip-text text-transparent"
                : ""
            ].join(" ")}
          >
            {activeTitle}
          </h1>
          <div
            className="relative"
            ref={orgMenuRef}
            onMouseEnter={() => setIsOrgMenuOpen(true)}
            onMouseLeave={() => setIsOrgMenuOpen(false)}
          >
            <button
              type="button"
              onFocus={() => setIsOrgMenuOpen(true)}
              className="inline-flex min-w-[220px] items-center justify-between rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-base font-medium text-slate-600 shadow-sm transition-all duration-300 hover:border-blue-300 hover:shadow"
            >
              <span className="max-w-[160px] truncate">{selectedOrg}</span>
              <ChevronDown
                className={[
                  "h-5 w-5 text-slate-500 transition-transform duration-200",
                  isOrgMenuOpen ? "rotate-180" : ""
                ].join(" ")}
              />
            </button>

            {isOrgMenuOpen ? (
              <div className="absolute right-0 top-14 z-20 w-[320px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
                <div className="relative border-b border-slate-200 bg-slate-50/40">
                  <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={orgSearch}
                    onChange={(event) => setOrgSearch(event.target.value)}
                    placeholder="Search"
                    className="h-12 w-full pl-12 pr-4 text-sm text-slate-700 outline-none placeholder:text-xs placeholder:text-slate-400"
                  />
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setSelectedOrg("My Organization");
                    setIsOrgMenuOpen(false);
                  }}
                  // Lighter blue classes applied here
                  className="group flex h-16 w-full items-center px-7 text-base font-medium bg-blue-400 text-white transition-all duration-200 hover:bg-blue-500"
                >
                  <span className="transition-transform duration-200 group-hover:translate-x-0.5">
                    My Organization
                  </span>
                </button>

                <div className="h-3 border-y border-slate-200 bg-slate-50" />

                <button
                  type="button"
                  className="group flex h-16 w-full items-center gap-2.5 px-7 text-base font-medium text-slate-900 transition-all duration-200 hover:bg-slate-50"
                >
                  <Plus className="h-5 w-5 text-blue-600 transition-transform duration-200 group-hover:scale-110" />
                  <span className="transition-transform duration-200 group-hover:translate-x-0.5">
                    Create Workspace
                  </span>
                </button>
              </div>
            ) : null}
          </div>
        </header>

        <div className="flex flex-1">
          {activeView === "email" ? (
            <EmailAccountsView />
          ) : activeView === "campaigns" ? (
            <CampaignsView />
          ) : (
            <section className="flex flex-1 items-center justify-center px-6 py-10">
              <p className="text-lg text-slate-500">{activeTitle} view coming soon</p>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}