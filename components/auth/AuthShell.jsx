"use client";

import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";

export default function AuthShell({
  title,
  subtitle,
  submitLabel,
  footerText,
  footerAction,
  footerHref
}) {
  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto grid min-h-screen max-w-7xl lg:grid-cols-2">
        <section className="flex items-center justify-center px-4 py-10 sm:px-6 lg:px-12">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="w-full max-w-md rounded-3xl border border-slate-200 bg-white p-8 shadow-lg shadow-slate-200/40"
          >
            <Link href="/" className="mb-8 flex items-center gap-2">
              <Image src="/icon.png" alt="CampaignPulse logo" width={34} height={34} />
              <span className="text-lg font-bold">CampaignPulse</span>
            </Link>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
            <p className="mt-2 text-sm text-slate-600">{subtitle}</p>
            <form className="mt-8 space-y-5">
              <Input label="Work email" type="email" />
              <Input label="Password" type="password" />
              <Button fullWidth>{submitLabel}</Button>
            </form>
            <div className="mt-6 space-y-3">
              <Button variant="secondary" fullWidth>
                Continue with Google
              </Button>
              <Button variant="secondary" fullWidth>
                Continue with Microsoft
              </Button>
            </div>
            <p className="mt-6 text-center text-sm text-slate-600">
              {footerText}{" "}
              <Link href={footerHref} className="font-semibold text-brand-600 hover:text-brand-700">
                {footerAction}
              </Link>
            </p>
          </motion.div>
        </section>
        <section className="relative hidden overflow-hidden bg-gradient-to-br from-brand-600 via-indigo-600 to-sky-500 lg:block">
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }}
            className="absolute inset-0"
          >
            <div className="absolute left-10 top-16 h-60 w-60 rounded-full bg-white/10 blur-3xl" />
            <div className="absolute bottom-10 right-10 h-72 w-72 rounded-full bg-sky-200/30 blur-3xl" />
          </motion.div>
          <div className="relative flex h-full flex-col justify-end p-12 text-white">
            <blockquote className="max-w-md text-lg font-medium leading-relaxed">
              &quot;CampaignPulse helped us triple reply rates while keeping domain health strong.
              The automation feels effortless.&quot;
            </blockquote>
            <p className="mt-4 text-sm text-sky-100">Head of Growth, Northloop Ventures</p>
          </div>
        </section>
      </div>
    </main>
  );
}
