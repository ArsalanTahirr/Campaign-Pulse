"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

function parseHashPayload() {
  const raw = window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "";
  const parsed = new URLSearchParams(raw);
  return {
    accessToken: parsed.get("access_token") || "",
    tokenType: parsed.get("token_type") || "bearer",
    userId: parsed.get("user_id") || "",
    email: parsed.get("email") || "",
  };
}

export default function OAuthCallbackPage() {
  const searchParams = useSearchParams();
  const provider = searchParams.get("provider") || "google";
  const status = searchParams.get("status") || "success";
  const [hydrated, setHydrated] = useState(false);
  const [email, setEmail] = useState("");
  const isSuccess = useMemo(() => status === "success", [status]);

  useEffect(() => {
    const payload = parseHashPayload();
    if (payload.accessToken) {
      // Linkage space for dashboard team:
      // replace localStorage with secure cookie/session exchange endpoint.
      localStorage.setItem("access_token", payload.accessToken);
      localStorage.setItem("token_type", payload.tokenType);
      localStorage.setItem("user_id", payload.userId);
      localStorage.setItem("email", payload.email);
    }
    setEmail(payload.email);
    setHydrated(true);
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className={`text-sm font-semibold ${isSuccess ? "text-emerald-600" : "text-amber-600"}`}>
          {isSuccess ? `${provider} sign-in successful` : `${provider} sign-in update`}
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
          {isSuccess ? "You are authenticated." : "Authentication status updated."}
        </h1>
        <p className="mt-4 text-sm leading-6 text-slate-600">
          {hydrated ? `Welcome${email ? `, ${email}` : ""}. You can continue to your app flow.` : "Finalizing sign-in..."}
        </p>
        <div className="mt-6 flex gap-3">
          <Link href="/login" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            Continue
          </Link>
          <Link href="/" className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            Home
          </Link>
        </div>
      </div>
    </main>
  );
}
