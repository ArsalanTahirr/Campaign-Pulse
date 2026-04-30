"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Loader2, XCircle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

/**
 * /invitations/accept/[token]
 *
 * Flow:
 *  1. Load the invitation details from GET /invitations/validate/{token}
 *  2. If user is not authenticated, redirect to /auth/login?invite_token=...
 *  3. If authenticated, accept invite immediately and redirect to /dashboard.
 */
export default function AcceptInvitationPage() {
  const { token } = useParams();
  const router = useRouter();

  const [validating, setValidating] = useState(true);
  const [validationError, setValidationError] = useState(null);
  const [statusText, setStatusText] = useState("Validating invitation...");

  useEffect(() => {
    if (!token) return;
    async function runAcceptFlow() {
      try {
        // 1) Validate token first (public route)
        const validateRes = await fetch(`${API}/invitations/validate/${token}`, {
          credentials: "include",
        });
        if (!validateRes.ok) {
          const err = await validateRes.json().catch(() => ({}));
          setValidationError(err.detail || "This invitation is no longer valid.");
          setValidating(false);
          return;
        }

        // 2) Check auth cookie via /auth/me
        const meRes = await fetch(`${API}/auth/me`, { credentials: "include" });
        if (meRes.status === 401) {
          router.replace(`/auth/login?invite_token=${encodeURIComponent(token)}`);
          // Keep spinner until the login page replaces this view (avoids a flash of the error state).
          return;
        }
        if (!meRes.ok) {
          setValidationError("Could not verify your session. Please log in again.");
          setValidating(false);
          return;
        }

        // 3) Authenticated: accept invitation and go to dashboard
        setStatusText("Accepting invitation...");
        const acceptRes = await fetch(`${API}/invitations/accept/${token}`, {
          method: "POST",
          credentials: "include",
        });
        if (!acceptRes.ok) {
          const err = await acceptRes.json().catch(() => ({}));
          const detail = err.detail;
          const msg =
            typeof detail === "string"
              ? detail
              : "Failed to accept invitation.";
          throw new Error(msg);
        }
        setStatusText("Invitation accepted. Redirecting...");
        router.replace("/dashboard");
        // Do not setValidating(false) on success — otherwise we briefly render the
        // fallback error UI before Next.js finishes navigation.
      } catch (e) {
        setValidationError(
          e instanceof Error
            ? e.message
            : "Could not process invitation right now. Please try again."
        );
        setValidating(false);
      }
    }
    runAcceptFlow();
  }, [token, router]);

  if (validating) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50">
        <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
        <p className="text-sm text-slate-500">{statusText}</p>
      </div>
    );
  }

  if (validationError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-4 text-center">
        <XCircle className="h-14 w-14 text-rose-400" />
        <h1 className="text-2xl font-bold text-slate-800">Invitation Invalid</h1>
        <p className="max-w-sm text-sm text-slate-500">{validationError}</p>
        <Link
          href="/dashboard"
          className="mt-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Go to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-4 text-center">
      <XCircle className="h-14 w-14 text-rose-400" />
      <h1 className="text-2xl font-bold text-slate-800">Invitation could not be accepted</h1>
      <p className="max-w-sm text-sm text-slate-500">{validationError || "Please try again."}</p>
      <Link
        href="/auth/login"
        className="mt-2 rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
      >
        Go to Login
      </Link>
    </div>
  );
}
