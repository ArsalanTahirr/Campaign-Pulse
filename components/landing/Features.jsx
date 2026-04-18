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
    <section className="section-shell py-16 sm:py-20">
      <div className="mb-10 text-center">
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Everything you need to scale outreach</h2>
        <p className="mt-3 text-slate-600">Powerful automation, clean UX, and enterprise-grade reliability.</p>
      </div>
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {FEATURE_ITEMS.map((feature, index) => {
          const Icon = ICON_MAP[feature.iconKey];
          return (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.2 }}
              transition={{ delay: index * 0.1, duration: 0.5 }}
            >
              <Card>
                {Icon ? <Icon className="mb-4 text-brand-600" /> : null}
                <h3 className="text-lg font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{feature.text}</p>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
