"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Home, Inbox, Mail, Send, Sparkles, TrendingUp, AlertCircle } from "lucide-react";
import DatePickerPopover from "@/components/ui/DatePickerPopover";
import GenderSelect from "@/components/ui/GenderSelect";

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
  "peer h-12 w-full rounded-xl border bg-white px-4 text-sm text-slate-900 outline-none transition duration-200 placeholder:text-transparent";

const floatingLabelClass =
  "pointer-events-none absolute left-4 top-1/2 z-[1] -translate-y-1/2 bg-white px-1 text-sm transition-all duration-200 peer-focus:top-0 peer-focus:-translate-y-0 peer-focus:text-xs peer-[:not(:placeholder-shown)]:top-0 peer-[:not(:placeholder-shown)]:-translate-y-0 peer-[:not(:placeholder-shown)]:text-xs";

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

function FloatingInput({ id, label, type = "text", value, onChange, autoComplete, className = "", error, ...rest }) {
  const errorInputClass = error
    ? "border-red-500 bg-red-50 focus:border-red-500 focus:ring-4 focus:ring-red-500/20 text-red-900 pr-10"
    : "border-slate-200 focus:border-brand-500 focus:shadow-glow focus:ring-4 focus:ring-brand-500/20 shadow-sm";
    
  const errorLabelClass = error
    ? "text-red-500 peer-focus:text-red-600 peer-[:not(:placeholder-shown)]:text-red-500"
    : "text-slate-500 peer-focus:text-brand-600";

  return (
    <div>
      <div className={`relative ${className} ${error ? "animate-shake" : ""}`}>
        <input
          id={id}
          type={type}
          placeholder=" "
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`${inputPeerClass} ${errorInputClass}`}
          {...rest}
        />
        <label htmlFor={id} className={`${floatingLabelClass} ${errorLabelClass}`}>
          {label}
        </label>
        {error && (
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
            <AlertCircle className="h-4 w-4 text-red-500" aria-hidden="true" />
          </div>
        )}
      </div>
      <div className={`grid transition-all duration-300 ease-in-out ${error ? "grid-rows-[1fr] opacity-100 mt-1.5" : "grid-rows-[0fr] opacity-0"}`}>
        <div className="overflow-hidden">
          <p className="text-xs text-red-600">{error}</p>
        </div>
      </div>
    </div>
  );
}

export default function SignupPage() {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const SIGNUP_ENDPOINT = process.env.NEXT_PUBLIC_SIGNUP_ENDPOINT || "/auth/signup";
  const GOOGLE_LOGIN_ENDPOINT = process.env.NEXT_PUBLIC_GOOGLE_LOGIN_ENDPOINT || "/auth/google/login";
  const [formData, setFormData] = useState({
    firstName: "",
    middleName: "",
    lastName: "",
    dob: "",
    gender: "",
    email: "",
    password: "",
    termsAccepted: false
  });
  const [currentStep, setCurrentStep] = useState(1);
  const [direction, setDirection] = useState(1);
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  function sanitizeTextInput(value) {
    return value.replace(/[<>&"'`]/g, "");
  }

  function sanitizeEmail(value) {
    return sanitizeTextInput(value).replace(/\s/g, "").toLowerCase();
  }

  function updateField(field, value) {
    const sanitizedValue = field === "email" ? sanitizeEmail(value) : sanitizeTextInput(value);
    setFormData((prev) => ({ ...prev, [field]: sanitizedValue }));
    setErrors((prev) => ({ ...prev, [field]: "" }));
    setSubmitError("");
  }

  function parseDateOnly(dateValue) {
    // Handles date inputs like "YYYY-MM-DD" in a timezone-stable way.
    if (typeof dateValue !== "string") return null;
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateValue);
    if (!match) return null;

    const year = Number(match[1]);
    const monthIndex = Number(match[2]) - 1; // JS months are 0-based
    const day = Number(match[3]);

    const date = new Date(year, monthIndex, day);
    // Guard against invalid dates like 2026-02-31 (JS will roll over).
    if (Number.isNaN(date.getTime())) return null;
    if (date.getFullYear() !== year || date.getMonth() !== monthIndex || date.getDate() !== day) return null;
    return date;
  }

  function isDobInFuture(dateOfBirth) {
    const dobDate = parseDateOnly(dateOfBirth);
    if (!dobDate) return false;

    const now = new Date();
    const todayDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return dobDate.getTime() > todayDate.getTime();
  }

  function isAtLeast18(dateOfBirth) {
    if (!dateOfBirth) return false;

    // Explicitly reject future DOBs.
    if (isDobInFuture(dateOfBirth)) return false;

    const dob = parseDateOnly(dateOfBirth);
    if (!dob) return false;

    const today = new Date();
    const todayDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());

    let age = todayDate.getFullYear() - dob.getFullYear();
    const monthDelta = todayDate.getMonth() - dob.getMonth();
    if (monthDelta < 0 || (monthDelta === 0 && todayDate.getDate() < dob.getDate())) {
      age -= 1;
    }
    return age >= 18;
  }

  function validateStep(step = currentStep) {
    const nextErrors = {};
    const trimmedFirstName = formData.firstName.trim();
    const trimmedLastName = formData.lastName.trim();
    const trimmedEmail = formData.email.trim();

    if (step === 1) {
      if (!trimmedFirstName || trimmedFirstName.length < 2) {
        nextErrors.firstName = "First name must be at least 2 characters.";
      }
      if (!trimmedLastName || trimmedLastName.length < 2) {
        nextErrors.lastName = "Last name must be at least 2 characters.";
      }
    }

    if (step === 2) {
      if (!formData.dob) {
        nextErrors.dob = "Please provide your date of birth.";
      } else if (isDobInFuture(formData.dob)) {
        nextErrors.dob = "Date of birth cannot be in the future.";
      } else if (!isAtLeast18(formData.dob)) {
        nextErrors.dob = "You must be 18 or older to register.";
      }
      if (!formData.gender) {
        nextErrors.gender = "Please indicate your gender.";
      }
    }

    if (step === 3) {
      if (!trimmedEmail) {
        nextErrors.email = "Please enter your email address.";
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
        nextErrors.email = "Please enter a valid email address.";
      }

      if (!formData.password) {
        nextErrors.password = "Please provide a password.";
      } else if (!/^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/.test(formData.password)) {
        nextErrors.password = "Password must contain at least 8 characters, including uppercase, number, and symbol.";
      }

      if (!formData.termsAccepted) {
        nextErrors.termsAccepted = "You must accept the Terms of Use and Privacy Policy.";
      }
    }

    setErrors((prev) => ({ ...prev, ...nextErrors }));
    return Object.keys(nextErrors).length === 0;
  }

  function validateSignupField(field) {
    const nextErrors = { ...errors };
    const value = formData[field] || "";
    
    if (field === "firstName") {
      if (!value.trim() || value.trim().length < 2) {
        nextErrors.firstName = "First name must be at least 2 characters.";
      } else delete nextErrors.firstName;
    }
    if (field === "lastName") {
      if (!value.trim() || value.trim().length < 2) {
        nextErrors.lastName = "Last name must be at least 2 characters.";
      } else delete nextErrors.lastName;
    }
    if (field === "dob") {
      if (!value) {
        nextErrors.dob = "Please provide your date of birth.";
      } else if (isDobInFuture(value)) {
        nextErrors.dob = "Date of birth cannot be in the future.";
      } else if (!isAtLeast18(value)) {
        nextErrors.dob = "You must be 18 or older to register.";
      } else delete nextErrors.dob;
    }
    if (field === "gender") {
      if (!value) nextErrors.gender = "Please indicate your gender.";
      else delete nextErrors.gender;
    }
    if (field === "email") {
      if (!value.trim()) {
        nextErrors.email = "Please enter your email address.";
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())) {
        nextErrors.email = "Please enter a valid email address.";
      } else delete nextErrors.email;
    }
    if (field === "password") {
      if (!value) {
        nextErrors.password = "Please provide a password.";
      } else if (!/^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/.test(value)) {
        nextErrors.password = "Password must contain at least 8 characters, including uppercase, number, and symbol.";
      } else delete nextErrors.password;
    }
    setErrors(nextErrors);
  }

  function goNext() {
    if (!validateStep(currentStep)) return;
    setDirection(1);
    setCurrentStep((s) => Math.min(3, s + 1));
  }

  function goBack() {
    setDirection(-1);
    setCurrentStep((s) => Math.max(1, s - 1));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validateStep(3)) return;

    setSubmitError("");
    setSuccessMessage("");
    setIsSubmitting(true);

    try {
      const payload = {
        first_name: formData.firstName.trim(),
        middle_name: formData.middleName.trim() || null,
        last_name: formData.lastName.trim(),
        date_of_birth: formData.dob,
        gender: formData.gender,
        email: formData.email.trim(),
        password: formData.password,
        terms_accepted: formData.termsAccepted
      };

      const response = await fetch(`${API_BASE_URL}${SIGNUP_ENDPOINT}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        let message = "Signup failed";
        try {
          const data = await response.json();
          if (typeof data?.detail === "string" && data.detail.trim()) {
            message = data.detail;
            if (
              response.status === 409 &&
              data.detail.toLowerCase().includes("google account")
            ) {
              message =
                'This email is already linked to a Google account. To add a login password, please click "Verify Email" to merge your accounts.';
            }
          }
        } catch {
          // Keep fallback message.
        }
        throw new Error(message);
      }

      let message = "We've sent a verification link to your email. Please open your inbox and click the link to activate your account.";
      try {
        const data = await response.json();
        if (typeof data?.detail === "string" && data.detail.trim()) {
          message = data.detail;
        }
      } catch {
        // Keep default success message.
      }
      setSuccessMessage(message);
    } catch (error) {
      setSubmitError(error?.message || "We couldn't complete signup right now. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleGoogleSignup() {
    window.location.assign(`${API_BASE_URL}${GOOGLE_LOGIN_ENDPOINT}`);
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
                        onBlur={() => validateSignupField("firstName")}
                        autoComplete="given-name"
                        error={errors.firstName}
                      />
                      <FloatingInput
                        id="lastName"
                        label="Last name"
                        value={formData.lastName}
                        onChange={(v) => updateField("lastName", v)}
                        onBlur={() => validateSignupField("lastName")}
                        autoComplete="family-name"
                        error={errors.lastName}
                      />
                    </div>
                    <FloatingInput
                      id="middleName"
                      label={<span>Middle name <span className="font-normal text-slate-400">(optional)</span></span>}
                      value={formData.middleName}
                      onChange={(v) => updateField("middleName", v)}
                      autoComplete="additional-name"
                    />

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
                      onClick={handleGoogleSignup}
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
                      <div className={errors.dob ? "animate-shake" : ""}>
                        <DatePickerPopover
                          id="dob"
                          value={formData.dob}
                          onChange={(v) => updateField("dob", v)}
                          onBlur={() => validateSignupField("dob")}
                          error={errors.dob}
                          placeholder="Select your birth date"
                        />
                      </div>
                    </div>

                    <div>
                      <label htmlFor="gender" className="mb-2 block text-sm font-medium text-slate-700">
                        Gender
                      </label>
                      <div className={errors.gender ? "animate-shake" : ""}>
                        <GenderSelect
                          id="gender"
                          value={formData.gender}
                          onChange={(v) => updateField("gender", v)}
                          onBlur={() => validateSignupField("gender")}
                          error={errors.gender}
                        />
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
                      onBlur={() => validateSignupField("email")}
                      autoComplete="email"
                      error={errors.email}
                    />

                    <div>
                      <div className={`relative ${errors.password ? "animate-shake" : ""}`}>
                        <input
                          id="signup-password"
                          type={showPassword ? "text" : "password"}
                          placeholder=" "
                          autoComplete="new-password"
                          value={formData.password}
                          onChange={(e) => updateField("password", e.target.value)}
                          onBlur={() => validateSignupField("password")}
                          className={`${inputPeerClass} ${
                            errors.password
                              ? "border-red-500 bg-red-50 text-red-900 focus:border-red-500 focus:ring-4 focus:ring-red-500/20"
                              : "border-slate-200 shadow-sm focus:border-brand-500 focus:shadow-glow focus:ring-4 focus:ring-brand-500/20"
                          } pr-14`}
                        />
                        <label htmlFor="signup-password" className={`${floatingLabelClass} ${
                          errors.password
                            ? "text-red-500 peer-focus:text-red-600 peer-[:not(:placeholder-shown)]:text-red-500"
                            : "text-slate-500 peer-focus:text-brand-600"
                        }`}>
                          Password
                        </label>
                        <div className="absolute inset-y-0 right-2 z-[2] flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => setShowPassword((v) => !v)}
                            className="h-8 rounded-md px-2 text-xs font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-700"
                          >
                            {showPassword ? "Hide" : "Show"}
                          </button>
                        </div>
                      </div>
                      <div className={`grid transition-all duration-300 ease-in-out ${errors.password ? "grid-rows-[1fr] opacity-100 mt-1.5" : "grid-rows-[0fr] opacity-0"}`}>
                        <div className="overflow-hidden">
                          <p className="text-xs text-red-600">{errors.password}</p>
                        </div>
                      </div>
                    </div>

                    <div>
                      <label className="flex cursor-pointer gap-3 text-sm leading-snug text-slate-600">
                        <input
                          type="checkbox"
                          checked={formData.termsAccepted}
                          onChange={(e) => {
                            setFormData((prev) => ({ ...prev, termsAccepted: e.target.checked }));
                            setErrors((prev) => ({ ...prev, termsAccepted: "" }));
                            setSubmitError("");
                          }}
                          className="mt-0.5 h-4 w-4 shrink-0 rounded border-slate-300 text-blue-600 focus:ring-blue-500/30"
                        />
                        <span className="text-sm text-slate-600">
                          I agree to the{" "}
                          <Link href="/terms" className="font-semibold text-brand-600 hover:underline">
                            Terms of Service
                          </Link>{" "}
                          and{" "}
                          <Link href="/privacy" className="font-semibold text-brand-600 hover:underline">
                            Privacy Policy
                          </Link>
                          .
                        </span>
                      </label>
                      <div className={`grid transition-all duration-300 ease-in-out ${errors.termsAccepted ? "grid-rows-[1fr] opacity-100 mt-1.5" : "grid-rows-[0fr] opacity-0"}`}>
                        <div className="overflow-hidden">
                          <p className="text-xs text-red-600">{errors.termsAccepted}</p>
                        </div>
                      </div>
                    </div>
                    <div className={`grid transition-all duration-300 ease-in-out ${submitError ? "grid-rows-[1fr] opacity-100 mt-1.5" : "grid-rows-[0fr] opacity-0"}`}>
                      <div className="overflow-hidden">
                        <p className="text-sm text-red-600">{submitError}</p>
                      </div>
                    </div>

                    {successMessage ? (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 shadow-sm"
                      >
                        <p className="text-sm font-semibold text-emerald-800">
                          Verification email sent
                        </p>
                        <p className="mt-1 text-sm leading-relaxed text-emerald-700">
                          {successMessage}
                        </p>
                        <p className="mt-2 text-xs text-emerald-700/90">
                          If you don't see it, check your spam or promotions folder.
                        </p>
                      </motion.div>
                    ) : (
                      <button
                        type="submit"
                        disabled={isSubmitting}
                        className="w-full rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/25 transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-70"
                      >
                        {isSubmitting ? "Creating account..." : "Join Now"}
                      </button>
                    )}
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
