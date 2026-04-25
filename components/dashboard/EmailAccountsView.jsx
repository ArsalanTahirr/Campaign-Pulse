"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Hand, Link2, Sparkles } from "lucide-react";

export default function EmailAccountsView({ hasContent = false, children = null }) {
  const [showWelcome, setShowWelcome] = useState(false);
  const [welcomeName, setWelcomeName] = useState("there");
  const hideTimerRef = useRef(null);
  const enterTimerRef = useRef(null);

  useEffect(() => {
    const storedName = (window.sessionStorage.getItem("welcomeFirstName") || "").trim();
    setWelcomeName(storedName || "there");
    window.sessionStorage.removeItem("welcomeFirstName");

    // Trigger slide-down shortly after mount so transition is visible.
    enterTimerRef.current = window.setTimeout(() => {
      setShowWelcome(true);
    }, 30);
    hideTimerRef.current = window.setTimeout(() => {
      setShowWelcome(false);
    }, 2250);

    return () => {
      if (enterTimerRef.current) window.clearTimeout(enterTimerRef.current);
      if (hideTimerRef.current) window.clearTimeout(hideTimerRef.current);
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

    async function loadCurrentUserName() {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) return;
        const user = await response.json();
        if (!isMounted) return;
        const resolvedFirstName =
          user?.first_name ||
          user?.firstName ||
          (user?.name ? String(user.name).trim().split(" ")[0] : "") ||
          "";
        if (resolvedFirstName) {
          setWelcomeName(resolvedFirstName);
        }
      } catch {
        // Keep banner functional even if profile lookup fails.
      }
    }

    loadCurrentUserName();
    return () => {
      isMounted = false;
    };
  }, []);

  if (hasContent) {
    return (
      <>
        <div
          className={`fixed left-1/2 top-6 z-[100] flex -translate-x-1/2 items-center justify-center rounded-[14px] bg-white px-8 py-3.5 text-[15px] font-medium tracking-wide text-slate-700 shadow-[0_8px_30px_rgb(0,0,0,0.08)] ring-1 ring-slate-100/50 transition-all duration-500 ease-in-out ${
            showWelcome ? "translate-y-0 opacity-100" : "-translate-y-24 opacity-0 pointer-events-none"
          }`}
          aria-live="polite"
          role="status"
        >
          Welcome back, {welcomeName}!
        </div>
        <section className="flex flex-1 px-6 py-10 sm:px-10">
          <div className="w-full">{children}</div>
        </section>
      </>
    );
  }

  return (
    <>
      <div
        className={`fixed left-1/2 top-6 z-[100] flex -translate-x-1/2 items-center justify-center rounded-[14px] bg-white px-8 py-3.5 text-[15px] font-medium tracking-wide text-slate-700 shadow-[0_8px_30px_rgb(0,0,0,0.08)] ring-1 ring-slate-100/50 transition-all duration-500 ease-in-out ${
          showWelcome ? "translate-y-0 opacity-100" : "-translate-y-24 opacity-0 pointer-events-none"
        }`}
        aria-live="polite"
        role="status"
      >
        Welcome back, {welcomeName}!
      </div>
      <section className="flex flex-1 items-center justify-center px-6 py-10 sm:px-10">
        <div className="flex w-full max-w-xl flex-col items-center gap-4 rounded-2xl bg-white/50 px-8 py-10 text-center backdrop-blur-sm">
          <Image
            src="/emailDood.png"
            alt="Email empty state doodle"
            width={800}
            height={800}
            className="h-auto w-full max-w-[460px] mix-blend-multiply"
            priority
          />

          <div className="mt-1 flex items-start justify-center gap-3 text-amber-500">
            <Hand
              fill="currentColor"
              className="mt-0.5 h-6 w-6 shrink-0 text-amber-500 stroke-amber-600 stroke-[1.4]"
            />
            <p className="text-lg font-semibold leading-tight text-slate-900 sm:text-xl">
              Add an email account to get started
            </p>
          </div>

          <button
            type="button"
            className="group mt-1 inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-base font-semibold text-blue-600 transition-all duration-300 hover:bg-blue-50 hover:text-blue-700"
          >
            <Link2 className="h-4 w-4 transition-transform duration-300 group-hover:scale-110" />
            Add New
          </button>
        </div>
      </section>
    </>
  );
}
