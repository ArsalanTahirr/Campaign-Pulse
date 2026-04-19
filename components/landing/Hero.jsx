"use client";

import { motion } from "framer-motion";
import { PlayCircle } from "lucide-react";
import Button from "@/components/ui/Button";
import { HERO_ANALYTICS_BARS } from "@/lib/constants/landing";

export default function Hero() {
  return (
    <section className="section-shell grid gap-12 py-20 lg:grid-cols-2 lg:items-center">
      <div>
        <p className="mb-4 inline-flex rounded-full border border-brand-100 bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
          Built for high-volume outreach teams
        </p>
        <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
          Launch winning campaigns with <span className="gradient-text">CampaignPulse</span>
        </h1>
        <p className="mt-6 max-w-xl text-base text-slate-600 sm:text-lg">
          Automate cold email at scale with inbox rotation, AI warmup, and campaign analytics
          that help your team book more meetings without hurting deliverability.
        </p>
        <div className="mt-8 flex flex-wrap gap-4">
          <Button>Start Free Trial</Button>
          <Button variant="secondary" className="gap-2">
            <PlayCircle size={16} /> Watch Demo
          </Button>
        </div>
      </div>
      <div className="relative lg:pl-8 [perspective:1400px]">
        <motion.div
          animate={{ x: [0, 8, 0], y: [0, -6, 0] }}
          transition={{ repeat: Infinity, duration: 9, ease: "easeInOut" }}
          className="pointer-events-none absolute -left-4 top-8 hidden h-24 w-24 rounded-2xl bg-gradient-to-br from-brand-200/60 to-sky-200/60 blur-sm sm:block"
        />
        <motion.div
          animate={{ x: [0, -6, 0], y: [0, 10, 0] }}
          transition={{ repeat: Infinity, duration: 11, ease: "easeInOut" }}
          className="pointer-events-none absolute -bottom-4 right-4 h-20 w-20 rounded-full bg-indigo-300/40 blur-md"
        />
        <motion.div
          animate={{ y: [0, -10, 0], rotateX: [8, 10, 8], rotateY: [-8, -6, -8] }}
          transition={{ repeat: Infinity, duration: 7.5, ease: "easeInOut" }}
          className="relative overflow-hidden rounded-[20px] border border-white/30 p-5 shadow-2xl shadow-brand-500/20 sm:p-6"
          style={{
            background: "rgba(255, 255, 255, 0.4)",
            backdropFilter: "blur(10px)",
            transformStyle: "preserve-3d"
          }}
        >
          <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-r from-brand-200/60 via-sky-200/60 to-indigo-200/60" />
          <div className="relative mt-12 space-y-4">
            <div className="flex items-center justify-between rounded-2xl border border-white/30 bg-white/65 p-4">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Email Analytics</p>
                <p className="mt-1 text-xl font-bold text-slate-900">41.8% Open Rate</p>
              </div>
              <div className="flex items-end gap-1">
                {HERO_ANALYTICS_BARS.map((bar, index) => (
                  <span
                    key={`${bar}-${index}`}
                    className="w-1.5 rounded-full bg-gradient-to-t from-brand-500 to-sky-400"
                    style={{ height: `${bar / 2}px` }}
                  />
                ))}
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-[1.4fr_1fr]">
              <div className="rounded-2xl border border-white/30 bg-white/70 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Recent Campaign Replies</p>
                <ul className="mt-3 space-y-3 text-sm text-slate-700">
                  <li className="flex items-center justify-between">
                    <span>Acme Ventures - Interested in a demo</span>
                    <span className="text-xs text-slate-500">2m ago</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>Northpeak Labs - Pricing request</span>
                    <span className="text-xs text-slate-500">10m ago</span>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>CloudVista - Booked call next week</span>
                    <span className="text-xs text-slate-500">24m ago</span>
                  </li>
                </ul>
              </div>
              <div className="space-y-4">
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">Live Status</p>
                  <p className="mt-2 text-lg font-bold text-emerald-900">3 Leads Generated Today</p>
                  <p className="mt-1 text-xs text-emerald-700">+14% vs yesterday</p>
                </div>
                <div className="rounded-2xl border border-white/30 bg-white/70 p-4">
                  <p className="text-xs text-slate-500">Unified Inbox Health</p>
                  <p className="mt-1 text-lg font-bold text-slate-900">96.2%</p>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
