"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, Plus, Search } from "lucide-react";
import { Space_Grotesk } from "next/font/google";
import { usePathname, useRouter } from "next/navigation";
import Sidebar from "@/components/dashboard/Sidebar";
import { toast } from "sonner";
import { useWorkspace } from "@/contexts/WorkspaceContext";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "700"],
});

const titleByPrefix = {
  "/dashboard/email-accounts": "Email Accounts",
  "/dashboard/campaigns": "Campaigns",
  "/dashboard/unibox": "Unibox",
  "/dashboard/analytics": "Analytics",
  "/dashboard/collaborators": "Collaborators",
};

export default function DashboardShell({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isOrgMenuOpen, setIsOrgMenuOpen] = useState(false);
  const [orgSearch, setOrgSearch] = useState("");
  const [currentUser, setCurrentUser] = useState(null);
  const { workspace, workspaces, switchWorkspace, createWorkspace } = useWorkspace();
  const [isCreatingWorkspace, setIsCreatingWorkspace] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [hasPendingWelcomeToast, setHasPendingWelcomeToast] = useState(false);
  const [fallbackWelcomeName, setFallbackWelcomeName] = useState("");
  const orgMenuRef = useRef(null);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (orgMenuRef.current && !orgMenuRef.current.contains(event.target)) {
        setIsOrgMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  useEffect(() => {
    let isMounted = true;
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

    async function loadCurrentUser() {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) return;
        const data = await response.json();
        if (!isMounted) return;
        setCurrentUser(data);
      } catch {
        // Keep dashboard usable even if profile fetch fails.
      }
    }

    loadCurrentUser();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    const currentParams = new URLSearchParams(window.location.search);
    const loginType = currentParams.get("login_type");
    const welcomeFromQuery = currentParams.get("welcome_name") || "";
    if (loginType === "google") {
      setHasPendingWelcomeToast(true);
      if (welcomeFromQuery) setFallbackWelcomeName(welcomeFromQuery);
      window.sessionStorage.setItem("dashboard_welcome_pending", "1");
      if (welcomeFromQuery) window.sessionStorage.setItem("dashboard_welcome_name", welcomeFromQuery);
      return;
    }
    const isPending = window.sessionStorage.getItem("dashboard_welcome_pending") === "1";
    if (!isPending) return;
    setHasPendingWelcomeToast(true);
    setFallbackWelcomeName(window.sessionStorage.getItem("dashboard_welcome_name") || "");
  }, []);

  useEffect(() => {
    if (!hasPendingWelcomeToast) return;
    const resolvedName =
      currentUser?.first_name ||
      currentUser?.firstName ||
      currentUser?.username ||
      currentUser?.name ||
      currentUser?.email?.split?.("@")?.[0] ||
      fallbackWelcomeName ||
      "User";
    toast.success(`Welcome back, ${resolvedName}!`, { duration: 2000 });
    setHasPendingWelcomeToast(false);
    window.sessionStorage.removeItem("dashboard_welcome_pending");
    window.sessionStorage.removeItem("dashboard_welcome_name");
    const currentParams = new URLSearchParams(window.location.search);
    if (currentParams.get("login_type")) {
      const cleanedParams = new URLSearchParams(currentParams.toString());
      cleanedParams.delete("login_type");
      cleanedParams.delete("welcome_name");
      const query = cleanedParams.toString();
      router.replace(`${pathname}${query ? `?${query}` : ""}`);
    }
  }, [hasPendingWelcomeToast, currentUser, fallbackWelcomeName, router, pathname]);

  async function handleLogout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
    } catch {
      // Redirect anyway to ensure user leaves protected area.
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  function handleSettings() {
    // Settings surface is planned; keep entry point in account menu.
  }

  async function handleCreateWorkspace(event) {
    event.preventDefault();
    const name = newWorkspaceName.trim();
    if (!name) return;
    try {
      await createWorkspace(name);
      toast.success(`Workspace "${name}" created!`);
      setNewWorkspaceName("");
      setIsCreatingWorkspace(false);
      setIsOrgMenuOpen(false);
    } catch (err) {
      toast.error(err.message || "Failed to create workspace.");
    }
  }

  const filteredWorkspaces = useMemo(() => {
    if (!orgSearch.trim()) return workspaces;
    return workspaces.filter((w) =>
      w.name.toLowerCase().includes(orgSearch.toLowerCase())
    );
  }, [workspaces, orgSearch]);

  const activeTitle = useMemo(() => {
    for (const [prefix, title] of Object.entries(titleByPrefix)) {
      if (pathname?.startsWith(prefix)) return title;
    }
    return "Dashboard";
  }, [pathname]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-50/60 transition-colors duration-300 dark:bg-slate-950">
      <Sidebar user={currentUser} onLogout={handleLogout} onSettings={handleSettings} />
      <main className="flex flex-1 flex-col overflow-hidden transition-colors duration-300">
        <header className="sticky top-0 z-50 flex h-20 items-center justify-between border-b border-slate-200 bg-white/95 px-6 backdrop-blur transition-colors duration-300 sm:px-8 dark:border-slate-800 dark:bg-slate-900/95">
          <h1
            className={[
              spaceGrotesk.className,
              "text-xl font-semibold tracking-tight text-slate-800 transition-all duration-300 sm:text-2xl dark:text-slate-100",
              activeTitle === "Email Accounts"
                ? "cursor-default bg-gradient-to-r from-sky-600 via-blue-600 to-cyan-500 bg-[length:200%_100%] bg-clip-text text-transparent"
                : "",
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
              className="inline-flex min-w-[220px] items-center justify-between rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-base font-medium text-slate-600 shadow-sm transition-all duration-300 hover:border-blue-300 hover:shadow dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
            >
              <span className="max-w-[160px] truncate">{workspace?.name || "Select Workspace"}</span>
              <ChevronDown
                className={[
                  "h-5 w-5 text-slate-500 transition-transform duration-200 dark:text-slate-400",
                  isOrgMenuOpen ? "rotate-180" : "",
                ].join(" ")}
              />
            </button>

            {isOrgMenuOpen ? (
              <div className="absolute right-0 top-14 z-20 w-[320px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900">
                <div className="relative border-b border-slate-200 bg-slate-50/40 dark:border-slate-700 dark:bg-slate-800/60">
                  <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    value={orgSearch}
                    onChange={(event) => setOrgSearch(event.target.value)}
                    placeholder="Search"
                    className="h-12 w-full pl-12 pr-4 text-sm text-slate-700 outline-none placeholder:text-xs placeholder:text-slate-400 dark:bg-transparent dark:text-slate-200"
                  />
                </div>

                {filteredWorkspaces.map((ws) => (
                  <button
                    key={ws.workspace_id}
                    type="button"
                    onClick={() => {
                      switchWorkspace(ws);
                      setIsOrgMenuOpen(false);
                    }}
                    className={[
                      "group flex h-16 w-full items-center px-7 text-base font-medium transition-all duration-200",
                      workspace?.workspace_id === ws.workspace_id
                        ? "bg-blue-400 text-white hover:bg-blue-500"
                        : "text-slate-900 hover:bg-slate-50 dark:text-slate-100 dark:hover:bg-slate-800",
                    ].join(" ")}
                  >
                    <span className="truncate transition-transform duration-200 group-hover:translate-x-0.5">
                      {ws.name}
                    </span>
                  </button>
                ))}

                <div className="h-3 border-y border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800" />

                {isCreatingWorkspace ? (
                  <form
                    onSubmit={handleCreateWorkspace}
                    className="flex items-center gap-2 px-4 py-3"
                  >
                    <input
                      autoFocus
                      type="text"
                      value={newWorkspaceName}
                      onChange={(e) => setNewWorkspaceName(e.target.value)}
                      placeholder="Workspace name…"
                      className="h-9 flex-1 rounded-lg border border-slate-200 px-3 text-sm text-slate-700 outline-none focus:border-blue-300"
                    />
                    <button
                      type="submit"
                      className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-700"
                    >
                      Create
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsCreatingWorkspace(false)}
                      className="rounded-lg px-2 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
                    >
                      Cancel
                    </button>
                  </form>
                ) : (
                  <button
                    type="button"
                    onClick={() => setIsCreatingWorkspace(true)}
                    className="group flex h-16 w-full items-center gap-2.5 px-7 text-base font-medium text-slate-900 transition-all duration-200 hover:bg-slate-50 dark:text-slate-100 dark:hover:bg-slate-800"
                  >
                    <Plus className="h-5 w-5 text-blue-600 transition-transform duration-200 group-hover:scale-110" />
                    <span className="transition-transform duration-200 group-hover:translate-x-0.5">
                      Create Workspace
                    </span>
                  </button>
                )}
              </div>
            ) : null}
          </div>
        </header>
        <div className="flex flex-1 overflow-y-auto transition-colors duration-300">{children}</div>
      </main>
    </div>
  );
}
