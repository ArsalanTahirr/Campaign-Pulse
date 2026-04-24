"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

export default function VerifyEmailResultPage() {
  const params = useSearchParams();
  const status = params.get("status") || "success";
  const message =
    params.get("message") || "Email verification completed. You can now log in.";
  const isSuccess = status === "success";

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto w-full max-w-xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className={`text-sm font-semibold ${isSuccess ? "text-emerald-600" : "text-amber-600"}`}>
          {isSuccess ? "Email Verified" : "Verification Update"}
        </p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
          {isSuccess ? "Your account is ready." : "Check your verification link."}
        </h1>
        <p className="mt-4 text-sm leading-6 text-slate-600">{message}</p>
        <div className="mt-6 flex gap-3">
          <Link href="/login" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
            Go to Login
          </Link>
          <Link href="/signup" className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
            Back to Signup
          </Link>
        </div>
      </div>
    </main>
  );
}
