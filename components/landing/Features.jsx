"use client";

import { motion } from "framer-motion";
import { BarChart3, Flame, MailCheck, ShieldCheck } from "lucide-react";
import Card from "@/components/ui/Card";
import { FEATURE_ITEMS } from "@/lib/constants/landing";

const ICON_MAP = {
  shield: ShieldCheck,
  flame: Flame,
  mail: MailCheck,
  chart: BarChart3
};

export default function Features() {
  return (
    <section className="section-shell relative py-20 sm:py-28">
      {/* Decorative background element */}
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-brand-50/50 via-transparent to-transparent" />
      
      <div className="mb-16 text-center">
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-5xl text-slate-900">
          Everything you need to <span className="gradient-text">scale outreach</span>
        </h2>
        <p className="mt-4 text-lg text-slate-600 max-w-2xl mx-auto">
          Powerful automation, clean UX, and enterprise-grade reliability designed for modern growth teams.
        </p>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {FEATURE_ITEMS.map((feature, index) => {
          const Icon = ICON_MAP[feature.iconKey];
          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ delay: index * 0.1, duration: 0.6, ease: "easeOut" }}
            >
              <Card className="h-full flex flex-col">
                {Icon ? (
                  <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-brand-100/50 transition-colors duration-300 group-hover:bg-brand-600 group-hover:text-white">
                    <Icon className="h-6 w-6" />
                  </div>
                ) : null}
                <h3 className="text-xl font-semibold text-slate-900">{feature.title}</h3>
                <p className="mt-3 text-sm text-slate-600 leading-relaxed flex-grow">{feature.text}</p>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
