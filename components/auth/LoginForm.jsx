"use client";

import { useCallback, useEffect, useId, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { X, Home, Inbox, Mail, Send, Sparkles, TrendingUp, Eye, EyeOff } from "lucide-react";

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
    <main className="min-h-screen lg:h-screen lg:overflow-hidden bg-white font-sans text-slate-900 antialiased">
      <div className="flex min-h-screen lg:h-screen">
        {/* Left: form */}
        <section className="relative flex w-full lg:w-1/2 xl:w-[55%] flex-col lg:overflow-y-auto">
          {/* Top Logo */}
          <div className="p-6 lg:p-8">
            <Link href="/" className="inline-flex items-center gap-2">
              <Image
                src="/icon.png"
                alt="CampaignPulse logo"
                width={28}
                height={28}
                className="h-7 w-7 object-contain"
              />
              <span className="text-lg font-bold text-slate-900 tracking-tight">CampaignPulse</span>
            </Link>
          </div>

          <div className="flex flex-1 flex-col justify-center px-6 pb-8 sm:pb-12 sm:px-10 lg:px-16 mx-auto w-full max-w-[420px]">
            <div className="mb-6 text-center">
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 tracking-tight">Welcome Back</h1>
              <p className="mt-2 text-sm text-gray-500 mx-auto max-w-[280px]">Enter your email and password to access your account.</p>
            </div>

            <form className="space-y-4 sm:space-y-5" action="#" method="post">
              <div>
                <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700 sm:mb-1.5">Email</label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="name@company.com"
                  className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2 sm:py-2.5 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700 sm:mb-1.5">Password</label>
                <div className="relative">
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    placeholder="Enter your password"
                    className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2 sm:py-2.5 pr-12 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute inset-y-0 right-3 my-auto flex items-center justify-center text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between gap-3 text-sm pt-1">
                <label htmlFor="remember" className="inline-flex cursor-pointer items-center gap-2 text-slate-500">
                  <input
                    id="remember"
                    name="remember"
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 focus:ring-opacity-50"
                  />
                  Remember Me
                </label>
                <button
                  type="button"
                  onClick={() => setForgotOpen(true)}
                  className="font-semibold text-blue-600 hover:text-blue-700"
                >
                  Forgot Password?
                </button>
              </div>

              <button
                type="submit"
                className="mt-2 w-full rounded-lg bg-[#3B42F6] px-4 py-2 sm:py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 shadow-md shadow-blue-500/20"
              >
                Log In
              </button>
            </form>

            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center" aria-hidden="true">
                <div className="w-full border-t border-slate-200" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-white px-4 text-slate-400">Or Login With</span>
              </div>
            </div>

            <div className="w-full">
              <button
                type="button"
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 sm:py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
              >
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" className="h-5 w-5">
                  <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303C33.656 32.657 29.205 36 24 36c-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.27 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z" />
                  <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 16.108 18.961 13 24 13c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.27 4 24 4 16.318 4 9.656 8.337 6.306 14.691z" />
                  <path fill="#4CAF50" d="M24 44c5.169 0 9.861-1.977 13.409-5.192l-6.19-5.238C29.143 35.091 26.715 36 24 36c-5.176 0-9.614-3.317-11.275-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z" />
                  <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.042 12.042 0 0 1-4.084 5.57h.001l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z" />
                </svg>
                Sign in with Google
              </button>
            </div>

            <p className="mt-8 text-center text-sm text-slate-500">
              Don't Have An Account?{" "}
              <Link href="/signup" className="font-semibold text-blue-600 hover:underline">
                Register Now.
              </Link>
            </p>
          </div>

          {/* Bottom Footer */}
          <div className="absolute bottom-6 left-6 right-6 flex justify-between text-sm text-gray-400 sm:bottom-10 sm:left-10 sm:right-10">
            <p>Copyright © 2026 CampaignPulse LTD.</p>
            <Link href="/privacy" className="hover:text-gray-600 hover:underline">Privacy Policy</Link>
          </div>
        </section>

        {/* Right: Graphic */}
        <section className="hidden lg:flex w-full lg:w-1/2 xl:w-[45%] p-4 lg:p-6">
          <div className="relative flex w-full flex-col overflow-hidden bg-[#3B42F6] rounded-[2.5rem] items-center justify-center p-8 xl:p-12 shadow-2xl">
            {/* Subtle geometric grid background */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff10_1px,transparent_1px),linear-gradient(to_bottom,#ffffff10_1px,transparent_1px)] bg-[size:4rem_4rem]" />
            
            {/* Radial glow */}
            <div className="pointer-events-none absolute left-1/2 top-1/2 h-[800px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-blue-400/20 blur-[120px]" />

          {/* Text Content */}
          <div className="relative z-10 w-full max-w-lg xl:max-w-xl text-left mb-8 xl:mb-12">
            <h2 className="text-3xl xl:text-4xl font-semibold leading-tight text-white mb-3 xl:mb-4">
              Supercharge your email<br />marketing campaigns.
            </h2>
            <p className="text-base xl:text-lg text-blue-100">
              Log in to access your marketing dashboard and grow your audience.
            </p>
          </div>

          {/* Dashboard Mockup */}
          <div className="relative z-10 w-full max-w-lg xl:max-w-xl rounded-xl bg-[#F8FAFC] p-4 shadow-2xl overflow-hidden h-[450px] scale-90 xl:scale-100 origin-center">
            {/* Top row cards */}
            <div className="flex gap-4 mb-4">
              {/* Sent Emails Card */}
              <div className="flex-1 rounded-xl bg-[#5A67D8] p-4 text-white shadow-sm">
                <div className="text-xs font-medium text-indigo-200 mb-1">Sent Emails</div>
                <div className="text-[10px] text-indigo-300 mb-2">Total emails delivered this month.</div>
                <div className="text-2xl font-bold mb-2">1.2M</div>
                <div className="inline-flex items-center gap-1 rounded bg-indigo-500/50 px-1.5 py-0.5 text-[10px]">
                  <span>↑ 12%</span>
                  <span className="text-indigo-200">From last month</span>
                </div>
              </div>
              
              {/* Open Rate Card */}
              <div className="flex-1 rounded-xl bg-white p-4 shadow-sm">
                <div className="text-xs font-medium text-slate-800 mb-1">Average Open Rate</div>
                <div className="text-[10px] text-slate-400 mb-2">Across all campaigns</div>
                <div className="text-2xl font-bold text-slate-800 mb-2">24.8%</div>
                {/* Fake line chart */}
                <svg viewBox="0 0 100 30" className="w-full h-8 text-blue-500 overflow-visible">
                  <path d="M0,20 C10,20 15,5 25,5 C35,5 40,25 50,25 C60,25 65,10 75,10 C85,10 90,15 100,15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M0,20 C10,20 15,5 25,5 C35,5 40,25 50,25 C60,25 65,10 75,10 C85,10 90,15 100,15 L100,30 L0,30 Z" fill="currentColor" fillOpacity="0.1" />
                </svg>
              </div>

              {/* Engagement Trends Chart Base */}
              <div className="flex-[1.5] rounded-xl bg-white p-4 shadow-sm relative">
                <div className="flex justify-between items-center mb-1">
                  <div className="text-xs font-medium text-slate-800">Engagement Trends</div>
                  <div className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded">Weekly ▼</div>
                </div>
                <div className="text-[10px] text-slate-400 mb-4">Monitor open and click rates for your campaigns.</div>
                {/* Fake bar chart behind */}
                <div className="flex items-end gap-2 h-20 opacity-30">
                  <div className="w-full bg-slate-200 rounded-t h-[40%]"></div>
                  <div className="w-full bg-blue-600 rounded-t h-[80%]"></div>
                  <div className="w-full bg-slate-200 rounded-t h-[60%]"></div>
                  <div className="w-full bg-slate-200 rounded-t h-[30%]"></div>
                </div>
              </div>
            </div>

            {/* Bottom Row - Table */}
            <div className="rounded-xl bg-white p-4 shadow-sm mb-4">
              <div className="text-xs font-medium text-slate-800 mb-1">Recent Campaigns</div>
              <div className="text-[10px] text-slate-400 mb-3">Performance of your latest broadcasts</div>
              
              <div className="w-full text-[10px]">
                <div className="flex text-slate-400 border-b border-slate-100 pb-2 mb-2">
                  <div className="w-8"></div>
                  <div className="flex-[2]">Campaign</div>
                  <div className="flex-[3]">Subject Line</div>
                  <div className="flex-[2]">Sent Date</div>
                  <div className="flex-[2]">Open Rate</div>
                  <div className="w-16">Status</div>
                </div>
                
                {[
                  { id: "Welcome Series", name: "Welcome to CampaignPulse!", date: "13 Feb, 2025", price: "42.5%", status: "Active" },
                  { id: "Monthly Newsletter", name: "Your Feb Updates & News", date: "10 Feb, 2025", price: "28.1%", status: "Sent" },
                  { id: "Promo Offer", name: "Save 20% on Annual Plans", date: "05 Feb, 2025", price: "15.4%", status: "Draft" },
                ].map((row, i) => (
                  <div key={i} className="flex items-center text-slate-600 py-1.5 border-b border-slate-50 last:border-0">
                    <div className="w-8 flex justify-center"><div className="w-2 h-2 rounded border border-slate-200 bg-white"></div></div>
                    <div className="flex-[2] font-medium text-slate-800">{row.id}</div>
                    <div className="flex-[3] flex items-center gap-1.5 truncate pr-2">
                      <div className="w-4 h-4 rounded bg-slate-100 flex-shrink-0 flex items-center justify-center text-[6px]">✉️</div>
                      <span className="truncate">{row.name}</span>
                    </div>
                    <div className="flex-[2]">{row.date}</div>
                    <div className="flex-[2] font-medium text-slate-800">{row.price}</div>
                    <div className="w-16">
                      <span className={`px-1.5 py-0.5 rounded-full text-[8px] font-medium ${row.status === 'Sent' ? 'bg-emerald-100 text-emerald-600' : row.status === 'Active' ? 'bg-blue-100 text-blue-600' : 'bg-amber-100 text-amber-600'}`}>
                        • {row.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Floating Donut Chart Card */}
            <div className="absolute right-4 top-20 w-64 rounded-xl bg-white p-5 shadow-2xl border border-slate-100">
              <div className="flex justify-between items-center mb-1">
                <div className="text-xs font-bold text-slate-800">Audience Breakdown</div>
                <div className="text-[9px] text-slate-400 bg-slate-50 border border-slate-100 px-1.5 py-0.5 rounded">All Time ▼</div>
              </div>
              <div className="text-[9px] text-slate-400 mb-6">Subscriber segments by engagement.</div>
              
              <div className="relative flex justify-center items-center h-28 mb-4">
                {/* SVG Donut Chart */}
                <svg viewBox="0 0 100 50" className="w-full h-full overflow-visible">
                  <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="#E2E8F0" strokeWidth="12" strokeLinecap="round" />
                  <path d="M 10 50 A 40 40 0 0 1 50 10" fill="none" stroke="#6366F1" strokeWidth="12" strokeLinecap="round" strokeDasharray="62.8" strokeDashoffset="0" />
                  <path d="M 50 10 A 40 40 0 0 1 90 50" fill="none" stroke="#A5B4FC" strokeWidth="12" strokeLinecap="round" strokeDasharray="62.8" strokeDashoffset="0" />
                </svg>
                <div className="absolute bottom-2 text-center bg-white rounded-full p-2 w-20 h-20 flex flex-col items-center justify-center shadow-[0_-4px_10px_rgba(0,0,0,0.05)] border-t border-slate-50">
                  <div className="text-[8px] text-slate-400">Total Subs</div>
                  <div className="text-sm font-bold text-slate-800 tracking-tight">14,204</div>
                </div>
              </div>

              <div className="space-y-1.5">
                {[
                  { color: "bg-[#6366F1]", label: "Highly Engaged", value: "8,245" },
                  { color: "bg-[#A5B4FC]", label: "Occasionally", value: "4,310" },
                  { color: "bg-slate-200", label: "Inactive", value: "1,649" },
                ].map((item, i) => (
                  <div key={i} className="flex justify-between items-center text-[9px]">
                    <div className="flex items-center gap-1.5 text-slate-600">
                      <div className={`w-1.5 h-1.5 rounded-full ${item.color}`}></div>
                      {item.label}
                    </div>
                    <div className="font-medium text-slate-800">{item.value}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
          </div>
        </section>

        {/* Forgot Password Modal */}
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
                      className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-blue-700"
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
                      className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm tracking-widest outline-none transition focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <button
                    type="submit"
                    className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-md transition hover:bg-blue-700"
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
                      className="font-medium text-blue-600 transition hover:text-blue-700"
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
    </main>
  );
}
