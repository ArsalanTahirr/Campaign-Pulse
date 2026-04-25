"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

export default function TermsPage() {
  const router = useRouter();

  function handleClose() {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
      return;
    }
    router.push("/auth/signup");
  }

  return (
    <main className="flex h-screen items-center justify-center bg-slate-50 px-6">
      <div className="text-center">
        <p className="text-2xl font-medium text-slate-800">
          Apko kia laga ham yeh bhi banaingai han? 😂
        </p>
        <button
          type="button"
          onClick={handleClose}
          className="mt-5 text-sm text-slate-500 transition hover:text-slate-700"
        >
          Back
        </button>
        <div className="mt-2">
          <Link href="/auth/signup" className="text-xs text-slate-400 transition hover:text-slate-600">
            Go to signup
          </Link>
        </div>
      </div>
    </main>
  );
}
