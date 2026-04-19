"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Home, Inbox, Mail, Send, Sparkles, TrendingUp } from "lucide-react";

function GoogleIcon({ className = "h-5 w-5" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden>
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

const inputPeerClass =
  "peer h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition duration-200 placeholder:text-transparent focus:border-brand-500 focus:shadow-glow focus:ring-4 focus:ring-brand-500/20";

const floatingLabelClass =
  "pointer-events-none absolute left-4 top-1/2 z-[1] -translate-y-1/2 bg-white px-1 text-sm text-slate-500 transition-all duration-200 peer-focus:top-0 peer-focus:-translate-y-0 peer-focus:text-xs peer-focus:text-brand-600 peer-[:not(:placeholder-shown)]:top-0 peer-[:not(:placeholder-shown)]:-translate-y-0 peer-[:not(:placeholder-shown)]:text-xs";

const stepVariants = {
  initial: (direction) => ({
    x: direction > 0 ? 48 : -48,
    opacity: 0
  }),
  animate: {
    x: 0,
    opacity: 1,
    transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] }
  },
  exit: (direction) => ({
    x: direction > 0 ? -48 : 48,
    opacity: 0,
    transition: { duration: 0.22, ease: [0.22, 1, 0.36, 1] }
  })
};

function FloatingInput({ id, label, type = "text", value, onChange, autoComplete, className = "", ...rest }) {
  return (
    <div className={`relative ${className}`}>
      <input
        id={id}
        type={type}
        placeholder=" "
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={inputPeerClass}
        {...rest}
      />
      <label htmlFor={id} className={floatingLabelClass}>
        {label}
      </label>
    </div>
  );
}

export default function SignupPage() {
  const [formData, setFormData] = useState({
    firstName: "",
    middleName: "",
    lastName: "",
    dob: "",
    gender: "",
    email: "",
    password: ""
  });
  const [currentStep, setCurrentStep] = useState(1);
  const [direction, setDirection] = useState(1);
  const [showPassword, setShowPassword] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);

  function updateField(field, value) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  function goNext() {
    setDirection(1);
    setCurrentStep((s) => Math.min(3, s + 1));
  }

  function goBack() {
    setDirection(-1);
    setCurrentStep((s) => Math.max(1, s - 1));
  }

  function handleSubmit(e) {
    e.preventDefault();
  }

  return (
    <main className="min-h-screen bg-white">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
        {/* Left: form */}
        <section className="relative flex min-h-screen flex-col items-center justify-center px-6 py-16 sm:px-10 lg:px-12">
          <Link
            href="/"
            className="absolute right-5 top-5 flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:border-slate-300 hover:text-slate-900 lg:hidden"
            aria-label="Home"
          >
            <Home className="h-5 w-5" strokeWidth={2} />
          </Link>

          <div className="w-full max-w-md">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Create a new account</h1>

            <div className="mt-6 flex gap-2" aria-hidden>
              {[1, 2, 3].map((step) => (
                <div
                  key={step}
                  className={`h-1.5 flex-1 rounded-full transition-colors duration-300 ${
                    step <= currentStep ? "bg-brand-600" : "bg-slate-200"
                  }`}
                />
              ))}
            </div>
            <p className="mt-2 text-center text-xs font-medium text-slate-400">
              Step {currentStep} of 3
            </p>

            <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
              <AnimatePresence mode="wait" custom={direction}>
                {currentStep === 1 && (
                  <motion.div
                    key="step-1"
                    custom={direction}
                    variants={stepVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    className="space-y-6"
                  >
                    <div className="grid grid-cols-2 gap-3">
                      <FloatingInput
                        id="firstName"
                        label="First name"
                        value={formData.firstName}
                        onChange={(v) => updateField("firstName", v)}
                        autoComplete="given-name"
                      />
                      <FloatingInput
                        id="lastName"
                        label="Last name"
                        value={formData.lastName}
                        onChange={(v) => updateField("lastName", v)}
                        autoComplete="family-name"
                      />
                    </div>
                    <div className="relative">
                      <input
                        id="middleName"
                        type="text"
                        placeholder=" "
                        autoComplete="additional-name"
                        value={formData.middleName}
                        onChange={(e) => updateField("middleName", e.target.value)}
                        className={inputPeerClass}
                      />
                      <label htmlFor="middleName" className={floatingLabelClass}>
                        Middle name <span className="font-normal text-slate-400">(optional)</span>
                      </label>
                    </div>

                    <button
                      type="button"
                      onClick={goNext}
                      className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/25 transition hover:bg-blue-700"
                    >
                      Next
                    </button>

                    <div className="relative">
                      <div className="absolute inset-0 flex items-center" aria-hidden>
                        <div className="w-full border-t border-slate-200" />
                      </div>
                      <div className="relative flex justify-center text-xs font-medium uppercase tracking-wide">
                        <span className="bg-white px-3 text-slate-400">OR</span>
                      </div>
                    </div>

                    <button
                      type="button"
                      className="flex w-full items-center justify-center gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-800 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
                    >
                      <GoogleIcon />
                      Sign Up with Google
                    </button>

                    <p className="text-center text-sm text-slate-600">
                      Already have an account?{" "}
                      <Link href="/login" className="font-bold text-slate-900 hover:text-blue-600">
                        Log In
                      </Link>
                    </p>
                  </motion.div>
                )}

                {currentStep === 2 && (
                  <motion.div
                    key="step-2"
                    custom={direction}
                    variants={stepVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    className="space-y-6"
                  >
                    <button
                      type="button"
                      onClick={goBack}
                      className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 transition hover:text-brand-600"
                    >
                      <ArrowLeft className="h-4 w-4" strokeWidth={2} />
                      Back
                    </button>

                    <div>
                      <label htmlFor="dob" className="mb-2 block text-sm font-medium text-slate-700">
                        Date of birth
                      </label>
                      <input
                        id="dob"
                        name="dob"
                        type="date"
                        value={formData.dob}
                        onChange={(e) => updateField("dob", e.target.value)}
                        className="h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-slate-900 shadow-sm outline-none transition [color-scheme:light] focus:border-brand-500 focus:shadow-glow focus:ring-4 focus:ring-brand-500/20"
                      />
                    </div>

                    <div>
                      <label htmlFor="gender" className="mb-2 block text-sm font-medium text-slate-700">
                        Gender
                      </label>
                      <div className="relative">
                        <select
                          id="gender"
                          name="gender"
                          value={formData.gender}
                          onChange={(e) => updateField("gender", e.target.value)}
                          className="h-12 w-full cursor-pointer appearance-none rounded-xl border border-slate-200 bg-white px-4 pr-10 text-sm text-slate-900 shadow-sm outline-none transition focus:border-brand-500 focus:shadow-glow focus:ring-4 focus:ring-brand-500/20"
                        >
                          <option value="">Select an option</option>
                          <option value="male">Male</option>
                          <option value="female">Female</option>
                          <option value="prefer_not">Prefer not to say</option>
                        </select>
                        <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">
                          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                        </span>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={goNext}
                      className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/25 transition hover:bg-blue-700"
                    >
                      Next
                    </button>
                  </motion.div>
                )}

                {currentStep === 3 && (
                  <motion.div
                    key="step-3"
                    custom={direction}
                    variants={stepVariants}
                    initial="initial"
                    animate="animate"
                    exit="exit"
                    className="space-y-6"
                  >
                    <button
                      type="button"
                      onClick={goBack}
                      className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 transition hover:text-brand-600"
                    >
                      <ArrowLeft className="h-4 w-4" strokeWidth={2} />
                      Back
                    </button>

                    <FloatingInput
                      id="signup-email"
                      label="Email"
                      type="email"
                      value={formData.email}
                      onChange={(v) => updateField("email", v)}
                      autoComplete="email"
                    />

                    <div>
                      <div className="relative">
                        <input
                          id="signup-password"
                          type={showPassword ? "text" : "password"}
                          placeholder=" "
                          autoComplete="new-password"
                          value={formData.password}
                          onChange={(e) => updateField("password", e.target.value)}
                          className={`${inputPeerClass} pr-14`}
                        />
                        <label htmlFor="signup-password" className={floatingLabelClass}>
                          Password
                        </label>
                        <button
                          type="button"
                          onClick={() => setShowPassword((v) => !v)}
                          className="absolute inset-y-0 right-3 z-[2] my-auto h-8 rounded-md px-2 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                        >
                          {showPassword ? "Hide" : "Show"}
                        </button>
                      </div>
                    </div>

                    <label className="flex cursor-pointer gap-3 text-sm leading-snug text-slate-600">
                      <input
                        type="checkbox"
                        checked={termsAccepted}
                        onChange={(e) => setTermsAccepted(e.target.checked)}
                        className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-blue-600 focus:ring-blue-500/30"
                      />
                      <span>
                        I agree to the CampaignPulse{" "}
                        <Link href="/terms" className="font-medium text-blue-600 hover:text-blue-700">
                          Terms of Use
                        </Link>{" "}
                        and{" "}
                        <Link href="/privacy" className="font-medium text-blue-600 hover:text-blue-700">
                          Privacy policy
                        </Link>
                        .
                      </span>
                    </label>

                    <button
                      type="submit"
                      className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/25 transition hover:bg-blue-700"
                    >
                      Join Now
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </form>
          </div>
        </section>

        {/* Right: graphic + testimonial (desktop only) */}
        <section
          className="relative hidden min-h-screen flex-col overflow-hidden bg-gradient-to-br from-slate-100 via-sky-50 to-slate-200/90 lg:flex"
          style={{ clipPath: "polygon(4% 0, 100% 0, 100% 100%, 0 100%)" }}
        >
          <div
            className="pointer-events-none absolute inset-0 opacity-40"
            style={{
              background:
                "radial-gradient(ellipse 80% 50% at 80% 20%, rgba(56, 189, 248, 0.25), transparent 50%), radial-gradient(ellipse 60% 40% at 10% 80%, rgba(148, 163, 184, 0.35), transparent 50%)"
            }}
          />

          <Link
            href="/"
            className="absolute right-8 top-8 z-10 flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white/90 text-slate-600 shadow-sm backdrop-blur-sm transition hover:bg-white hover:text-slate-900"
            aria-label="Home"
          >
            <Home className="h-5 w-5" strokeWidth={2} />
          </Link>

          <div className="relative z-[1] flex flex-1 flex-col items-center justify-center px-12 pb-16 pt-24">
            <div className="mb-12 flex aspect-square w-full max-w-sm items-center justify-center rounded-3xl border border-slate-200/80 bg-white/60 p-10 shadow-lg shadow-slate-300/40 backdrop-blur-sm">
              <div className="grid grid-cols-2 gap-6 text-slate-700">
                <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-sky-100/90 text-sky-600">
                  <Mail className="h-9 w-9" strokeWidth={1.75} />
                </div>
                <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-indigo-100/90 text-indigo-600">
                  <Send className="h-9 w-9" strokeWidth={1.75} />
                </div>
                <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-emerald-100/90 text-emerald-600">
                  <Inbox className="h-9 w-9" strokeWidth={1.75} />
                </div>
                <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-violet-100/90 text-violet-600">
                  <TrendingUp className="h-9 w-9" strokeWidth={1.75} />
                </div>
                <div className="col-span-2 flex h-16 items-center justify-center gap-2 rounded-2xl border border-dashed border-slate-300/80 bg-slate-50/80 text-sm font-medium text-slate-500">
                  <Sparkles className="h-5 w-5 text-amber-500" />
                  Outreach that converts
                </div>
              </div>
            </div>

            <div className="max-w-md text-center lg:text-left">
              <p className="text-2xl font-bold leading-tight tracking-tight text-slate-900 sm:text-3xl">
                45,000+ clients are getting more replies!
              </p>
              <p className="mt-4 text-base leading-relaxed text-slate-600">
                Unlock the power of effective outreach with our cutting-edge platform, and experience a surge in
                responses and engagement rates like never before.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
