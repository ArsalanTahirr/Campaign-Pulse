"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Inbox,
  Mail,
  Megaphone,
  Settings,
  User
} from "lucide-react";

const navItems = [
  { id: "email-accounts", href: "/dashboard/email-accounts", label: "Email Accounts", icon: Mail },
  { id: "campaigns", href: "/dashboard/campaigns", label: "Campaigns", icon: Megaphone },
  { id: "unibox", href: "/dashboard/unibox", label: "Unibox", icon: Inbox },
  { id: "analytics", href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 }
];

export default function Sidebar() {
  const pathname = usePathname();
  const baseIconButtonClass =
    "mx-auto flex h-11 w-11 items-center justify-center rounded-xl text-slate-500 transition-all duration-200 hover:scale-105 hover:bg-slate-100 hover:text-blue-600";

  return (
    <aside className="h-screen w-24 shrink-0 border-r border-slate-200 bg-white">
      <div className="flex h-full flex-col px-4 py-6">
        <div className="flex justify-center pb-8">
          <Link
            href="/"
            aria-label="Home"
            className="group relative flex items-center justify-center rounded-xl p-1.5 transition-all duration-200 hover:scale-105 hover:bg-slate-100"
          >
            <Image
              src="/icon.png"
              alt="Campaign Pulse"
              width={50}
              height={50}
              priority
              className="h-11 w-11 rounded-lg object-contain transition-transform duration-300 group-hover:rotate-3"
            />
            <span className="pointer-events-none absolute left-14 top-1/2 -translate-y-1/2 rounded-md bg-slate-900 px-2 py-1 text-xs font-medium text-white opacity-0 shadow-sm transition-all duration-200 group-hover:translate-x-1 group-hover:opacity-100">
              Campaign Pulse
            </span>
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
                      ? "bg-blue-50 text-blue-600"
                      : ""
                  ].join(" ")}
                >
                  <Icon className="h-5 w-5" />
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="mt-auto space-y-3 pt-8">
          <button
            type="button"
            aria-label="Settings"
            title="Settings"
            className={baseIconButtonClass}
          >
            <Settings className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Profile"
            title="Profile"
            className={baseIconButtonClass}
          >
            <User className="h-5 w-5" />
          </button>
        </div>
      </div>
    </aside>
  );
}
