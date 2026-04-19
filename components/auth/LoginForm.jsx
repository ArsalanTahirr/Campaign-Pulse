"use client";

import { useCallback, useEffect, useId, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { X } from "lucide-react";

export default function LoginForm() {
  const [showPassword, setShowPassword] = useState(false);
  const forgotTitleId = useId();
  const forgotDescId = useId();

  const [forgotOpen, setForgotOpen] = useState(false);
  const [resetStep, setResetStep] = useState("email");
  const [resetEmail, setResetEmail] = useState("");
  const [resetCode, setResetCode] = useState("");
  const [resetMessage, setResetMessage] = useState("");

  const closeForgotModal = useCallback(() => {
    setForgotOpen(false);
    setResetStep("email");
    setResetEmail("");
    setResetCode("");
    setResetMessage("");
  }, []);

  useEffect(() => {
    if (!forgotOpen) return;
    function onKeyDown(e) {
      if (e.key === "Escape") closeForgotModal();
    }
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [forgotOpen, closeForgotModal]);

  function handleSendCode(e) {
    e.preventDefault();
    if (!resetEmail.trim()) {
      setResetMessage("Please enter your email address.");
      return;
    }
    setResetMessage("");
    setResetStep("code");
  }

  function handleVerifyCode(e) {
    e.preventDefault();
    if (!resetCode.trim()) {
      setResetMessage("Please enter the code from your email.");
      return;
    }
    setResetMessage("");
    closeForgotModal();
  }

  function handleResendCode() {
    setResetCode("");
    setResetMessage("A new code has been sent (demo — connect your API to send real emails).");
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900 antialiased">
      <div className="relative flex min-h-screen items-center justify-center px-4 py-12 sm:px-6">
        <div
          className="pointer-events-none absolute -right-16 -top-16 h-64 w-64 rounded-full bg-gradient-to-br from-pulseTeal/25 to-pulseBlue/25 blur-3xl sm:h-80 sm:w-80"
          aria-hidden
        />
        <Link
          href="/"
          aria-label="Go to home page"
          className="absolute right-4 top-4 inline-flex h-11 w-11 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-pulseTeal hover:text-pulseTeal sm:right-6 sm:top-6"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="h-5 w-5"
          >
            <path d="M3 10.5 12 3l9 7.5" />
            <path d="M5.5 9.5V21h13V9.5" />
            <path d="M9.5 21v-6h5v6" />
          </svg>
        </Link>

        <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl sm:p-8">
          <div className="mb-8 text-center">
            <Image
              src="/icon.png"
              alt="CampaignPulse icon"
              width={48}
              height={48}
              className="mx-auto h-12 w-12 object-contain"
            />
            <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-slate-900">Welcome Back</h1>
            <p className="mt-2 text-sm text-slate-500">Sign in to continue to CampaignPulse</p>
          </div>

          <form className="space-y-5" action="#" method="post">
            <button
              type="button"
              className="flex w-full items-center justify-center gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" className="h-5 w-5">
                <path
                  fill="#FFC107"
                  d="M43.611 20.083H42V20H24v8h11.303C33.656 32.657 29.205 36 24 36c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.27 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
                />
                <path
                  fill="#FF3D00"
                  d="M6.306 14.691l6.571 4.819C14.655 16.108 18.961 13 24 13c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.27 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
                />
                <path
                  fill="#4CAF50"
                  d="M24 44c5.169 0 9.861-1.977 13.409-5.192l-6.19-5.238C29.143 35.091 26.715 36 24 36c-5.176 0-9.614-3.317-11.275-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
                />
                <path
                  fill="#1976D2"
                  d="M43.611 20.083H42V20H24v8h11.303a12.042 12.042 0 0 1-4.084 5.57h.001l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"
                />
              </svg>
              Sign in with Google
            </button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center" aria-hidden="true">
                <div className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-white px-3 text-xs font-medium uppercase tracking-wide text-slate-400">
                  or sign in with email
                </span>
              </div>
            </div>

            <div>
              <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="you@example.com"
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-pulseTeal focus:ring-2 focus:ring-pulseBlue/30"
              />
            </div>

            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-700">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  placeholder="Enter your password"
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 pr-12 text-sm outline-none transition focus:border-pulseTeal focus:ring-2 focus:ring-pulseBlue/30"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-3 my-auto h-8 rounded-md px-2 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between gap-3 text-sm">
              <label htmlFor="remember" className="inline-flex cursor-pointer items-center gap-2 text-slate-600">
                <input
                  id="remember"
                  name="remember"
                  type="checkbox"
                  className="h-4 w-4 rounded border-slate-300 text-pulseTeal focus:ring-pulseBlue/40"
                />
                Remember me
              </label>
              <button
                type="button"
                onClick={() => setForgotOpen(true)}
                className="font-medium text-pulseBlue transition hover:text-pulseTeal"
              >
                Forgot password?
              </button>
            </div>

            <button
              type="submit"
              className="w-full rounded-xl bg-gradient-to-r from-pulseTeal to-pulseBlue px-4 py-3 text-sm font-semibold text-white shadow-md transition duration-300 hover:scale-[1.01] focus:outline-none focus:ring-2 focus:ring-pulseBlue/40 focus:ring-offset-2"
            >
              Sign In
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600">
            New here?{" "}
            <Link href="/signup" className="font-semibold text-pulseBlue transition hover:text-pulseTeal">
              Create account
            </Link>
          </p>
        </div>

        {forgotOpen ? (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            role="presentation"
            onClick={(e) => {
              if (e.target === e.currentTarget) closeForgotModal();
            }}
          >
            <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" aria-hidden />
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby={forgotTitleId}
              aria-describedby={forgotDescId}
              className="relative z-10 w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl sm:p-8"
            >
              <button
                type="button"
                onClick={closeForgotModal}
                className="absolute right-4 top-4 rounded-lg p-2 text-slate-500 transition hover:bg-slate-100 hover:text-slate-800"
                aria-label="Close"
              >
                <X className="h-5 w-5" strokeWidth={2} />
              </button>

              <h2 id={forgotTitleId} className="pr-10 text-xl font-bold tracking-tight text-slate-900">
                {resetStep === "email" ? "Verify your email" : "Enter verification code"}
              </h2>
              <p id={forgotDescId} className="mt-2 text-sm text-slate-600">
                {resetStep === "email"
                  ? "We’ll send a one-time code to your email so you can reset your password."
                  : `We sent a code to ${resetEmail.trim() || "your email"}. Enter it below.`}
              </p>

              {resetMessage ? (
                <p
                  className={`mt-4 rounded-xl border px-3 py-2 text-sm ${
                    resetMessage.startsWith("Please")
                      ? "border-amber-200 bg-amber-50 text-amber-900"
                      : "border-emerald-200 bg-emerald-50 text-emerald-900"
                  }`}
                  role="status"
                >
                  {resetMessage}
                </p>
              ) : null}

              {resetStep === "email" ? (
                <form className="mt-6 space-y-4" onSubmit={handleSendCode}>
                  <div>
                    <label htmlFor="reset-email" className="mb-2 block text-sm font-medium text-slate-700">
                      Email
                    </label>
                    <input
                      id="reset-email"
                      name="reset-email"
                      type="email"
                      autoComplete="email"
                      value={resetEmail}
                      onChange={(e) => setResetEmail(e.target.value)}
                      placeholder="you@example.com"
                      className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-pulseTeal focus:ring-2 focus:ring-pulseBlue/30"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full rounded-xl bg-gradient-to-r from-pulseTeal to-pulseBlue px-4 py-3 text-sm font-semibold text-white shadow-md transition duration-300 hover:scale-[1.01] focus:outline-none focus:ring-2 focus:ring-pulseBlue/40 focus:ring-offset-2"
                  >
                    Send verification code
                  </button>
                </form>
              ) : (
                <form className="mt-6 space-y-4" onSubmit={handleVerifyCode}>
                  <div>
                    <label htmlFor="reset-code" className="mb-2 block text-sm font-medium text-slate-700">
                      Verification code
                    </label>
                    <input
                      id="reset-code"
                      name="reset-code"
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      value={resetCode}
                      onChange={(e) => setResetCode(e.target.value.replace(/\s/g, ""))}
                      placeholder="Enter code from email"
                      className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm tracking-widest outline-none transition focus:border-pulseTeal focus:ring-2 focus:ring-pulseBlue/30"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full rounded-xl bg-gradient-to-r from-pulseTeal to-pulseBlue px-4 py-3 text-sm font-semibold text-white shadow-md transition duration-300 hover:scale-[1.01] focus:outline-none focus:ring-2 focus:ring-pulseBlue/40 focus:ring-offset-2"
                  >
                    Verify code
                  </button>
                  <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                    <button
                      type="button"
                      onClick={() => {
                        setResetStep("email");
                        setResetCode("");
                        setResetMessage("");
                      }}
                      className="font-medium text-slate-600 underline-offset-2 transition hover:text-slate-900 hover:underline"
                    >
                      Use a different email
                    </button>
                    <button
                      type="button"
                      onClick={handleResendCode}
                      className="font-medium text-pulseBlue transition hover:text-pulseTeal"
                    >
                      Resend code
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
