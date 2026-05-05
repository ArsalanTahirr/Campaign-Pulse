"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";
import {
  BarChart3,
  LogOut,
  Inbox,
  Mail,
  Megaphone,
  Settings,
  Users2,
} from "lucide-react";

const navItems = [
  { id: "email-accounts", href: "/dashboard/email-accounts", label: "Email Accounts", icon: Mail },
  { id: "campaigns", href: "/dashboard/campaigns", label: "Campaigns", icon: Megaphone },
  { id: "collaborators", href: "/dashboard/collaborators", label: "Collaborators", icon: Users2 },
  { id: "unibox", href: "/dashboard/unibox", label: "Unibox", icon: Inbox },
  { id: "analytics", href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
];

export default function Sidebar({ user, onLogout, onSettings }) {
  const pathname = usePathname();
  const profileMenuRef = useRef(null);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [isThemeMounted, setIsThemeMounted] = useState(false);
  const { theme, setTheme } = useTheme();
  const baseIconButtonClass =
    "mx-auto flex h-11 w-11 items-center justify-center rounded-xl text-slate-500 transition-all duration-200 hover:scale-105 hover:bg-slate-100 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-sky-400";
  const fullNameFromParts = [user?.first_name || user?.firstName, user?.last_name || user?.lastName]
    .filter(Boolean)
    .join(" ")
    .trim();
  const accountName = fullNameFromParts || user?.name || user?.username || user?.email || "User";
  const accountEmail = user?.email || "";
  const avatarInitial = useMemo(() => accountName.trim().charAt(0).toUpperCase() || "U", [accountName]);

  useEffect(() => {
    setIsThemeMounted(true);
  }, []);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target)) {
        setIsProfileMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  const activeTheme = isThemeMounted ? theme || "system" : "system";

  return (
    <aside className="h-screen w-24 shrink-0 border-r border-slate-200 bg-white transition-colors duration-300 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex h-full flex-col px-4 py-6">
        <div className="flex justify-center pb-8">
          <Link href="/dashboard" aria-label="Go to dashboard" className="cursor-pointer">
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: "spring", stiffness: 400, damping: 20 }}
              className="flex h-11 w-11 items-center justify-center rounded-xl"
            >
              <Image
                src="/icon.png"
                alt="CampaignPulse"
                width={50}
                height={50}
                priority
                className="h-11 w-11 rounded-lg object-contain"
              />
            </motion.div>
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center">
          <nav className="flex flex-col gap-6">
            {navItems.map(({ id, href, label, icon: Icon }) => {
              const isActive = pathname === href || pathname?.startsWith(`${href}/`);

              return (
                <Link
                  key={id}
                  href={href}
                  aria-label={label}
                  title={label}
                  className={[
                    baseIconButtonClass,
                    isActive
                      ? "bg-blue-50 text-blue-600 dark:bg-slate-800 dark:text-sky-400"
                      : ""
                  ].join(" ")}
                >
                  <Icon className="h-5 w-5" />
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-auto pt-8">
          <div className="relative" ref={profileMenuRef}>
            {isProfileMenuOpen ? (
              <div className="absolute bottom-14 left-0 z-40 w-72 rounded-2xl border border-slate-200/90 bg-white/95 p-4 shadow-[0_20px_45px_rgba(15,23,42,0.16)] backdrop-blur-md transition-colors duration-300 dark:border-slate-700 dark:bg-slate-900/95">
                <div className="flex items-center gap-3 rounded-xl bg-slate-50 px-3 py-3 transition-colors duration-300 dark:bg-slate-800">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-brand-600 to-sky-500 text-sm font-semibold text-white">
                    {avatarInitial}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">{accountName}</p>
                    <p className="truncate text-xs text-slate-500 dark:text-slate-400">{accountEmail || "No email found"}</p>
                  </div>
                </div>

                <div className="mt-4 border-t border-slate-200 pt-4 dark:border-slate-700">
                  <p className="mb-2 text-left text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">Theme</p>
                  <div className="grid grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
                    {["light", "dark", "system"].map((mode) => (
                      <button
                        key={mode}
                        type="button"
                        onClick={() => setTheme(mode)}
                        className={`rounded-lg px-2 py-1.5 text-xs font-semibold capitalize transition ${
                          activeTheme === mode
                            ? "bg-white text-slate-800 shadow-sm dark:bg-slate-700 dark:text-slate-100"
                            : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                        }`}
                      >
                        {mode}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="mt-4 border-t border-slate-200 pt-3 dark:border-slate-700">
                  <button
                    type="button"
                    onClick={() => {
                      onSettings?.();
                      setIsProfileMenuOpen(false);
                    }}
                    className="flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-sm text-slate-700 transition hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    <Settings className="h-4.5 w-4.5 text-slate-500 dark:text-slate-400" />
                    Settings
                  </button>
                  <button
                    type="button"
                    onClick={onLogout}
                    className="mt-1 flex w-full items-center gap-2 rounded-xl px-2.5 py-2 text-sm text-slate-700 transition hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800"
                  >
                    <LogOut className="h-4.5 w-4.5 text-slate-500 dark:text-slate-400" />
                    Logout
                  </button>
                </div>
              </div>
            ) : null}

            <button
              type="button"
              aria-label="Profile"
              title="Profile"
              onClick={() => setIsProfileMenuOpen((prev) => !prev)}
              className="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-brand-600 to-sky-500 text-sm font-semibold text-white shadow-md shadow-sky-500/35 transition-all duration-200 hover:scale-105"
            >
              {avatarInitial}
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
