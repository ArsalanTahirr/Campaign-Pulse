"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useScroll, useSpring, useInView } from "framer-motion";

// ─── Data ────────────────────────────────────────────────────────────────────

const sections = [
  {
    id: "acceptance",
    number: "1",
    title: "Acceptance of Terms",
    body: [
      "By creating an account or using any part of the CampaignPulse platform ('Service'), you confirm that you are at least 18 years old, have the legal authority to enter into this agreement, and accept these Terms of Service in full.",
      "If you are using CampaignPulse on behalf of an organisation, you represent that you have the authority to bind that organisation to these terms. In that case, 'you' and 'your' refer to both you personally and that organisation.",
      "We reserve the right to update these Terms at any time. Continued use of the Service after changes are published constitutes acceptance of the revised Terms.",
    ],
  },
  {
    id: "email-compliance",
    number: "2",
    title: "Email Compliance & Anti-Spam Policy",
    body: [
      "CampaignPulse is designed exclusively for lawful, permission-based outreach. You must comply with all applicable anti-spam legislation including, but not limited to, the CAN-SPAM Act (United States), GDPR (European Union), CASL (Canada), and any other laws applicable in your jurisdiction.",
      "You are solely responsible for ensuring that every recipient in your campaign has given appropriate consent to receive commercial emails. You must honour opt-out requests immediately — within 10 business days as required by CAN-SPAM — and must never send email to an address that has previously unsubscribed.",
      "Prohibited uses include: sending unsolicited bulk email (spam), purchasing or scraping email lists without verifiable consent, impersonating another person or entity, including false or misleading header information, and using deceptive subject lines. Violation of this clause will result in immediate account termination and may be reported to relevant authorities.",
    ],
  },
  {
    id: "account-usage",
    number: "3",
    title: "Account Usage & Sender Pool Limits",
    body: [
      "Each CampaignPulse subscription tier entitles you to connect a defined maximum number of sending accounts ('sender pool'). These limits are outlined in your chosen plan at the time of sign-up. Attempting to circumvent pool limits — for example by creating multiple accounts or sharing credentials — is a material breach of these Terms.",
      "Automated warmup is a feature provided to gradually increase your sending reputation. You agree not to use the warmup engine to artificially inflate engagement metrics, misrepresent open or reply rates to third parties, or circumvent email provider sending limits in a way that violates those providers' own terms of service.",
      "CampaignPulse reserves the right to rate-limit, suspend, or permanently disable any sender account that exhibits sending patterns consistent with spam, abuse, or violations of email provider policies — with or without prior notice.",
    ],
  },
  {
    id: "intellectual-property",
    number: "4",
    title: "Intellectual Property",
    body: [
      "All software, algorithms, designs, logos, and written content on the CampaignPulse platform are the exclusive intellectual property of CampaignPulse and its licensors. Nothing in these Terms transfers any ownership rights to you.",
      "You grant CampaignPulse a limited, non-exclusive, royalty-free licence to store and process the data you upload (contacts, email copy, campaign configurations) solely for the purpose of providing the Service to you. We will never sell your data to third parties.",
      "Any feedback, suggestions, or feature requests you submit may be used by CampaignPulse without restriction or compensation.",
    ],
  },
  {
    id: "liability",
    number: "5",
    title: "Limitation of Liability",
    body: [
      "CampaignPulse is a software tool designed to streamline cold email outreach. We do not guarantee any specific reply rates, open rates, meeting bookings, revenue outcomes, or business results. Campaign performance depends on factors entirely outside our control, including the quality of your email copy, target audience, offer, and deliverability of your sending domain.",
      "To the maximum extent permitted by law, CampaignPulse, its directors, employees, and affiliates shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of — or inability to use — the Service, even if we have been advised of the possibility of such damages.",
      "Our total aggregate liability to you for any claims arising from these Terms or the Service shall not exceed the amount you paid to CampaignPulse in the 12 months immediately preceding the event giving rise to the claim.",
    ],
  },
  {
    id: "termination",
    number: "6",
    title: "Termination",
    body: [
      "You may cancel your account at any time from your account settings. Cancellation takes effect at the end of your current billing period; no partial refunds are issued for unused time.",
      "We may suspend or terminate your access immediately, without prior notice or liability, if you breach any provision of these Terms, engage in conduct that we determine (in our sole discretion) to be harmful to other users, third parties, or the reputation of CampaignPulse.",
      "Upon termination, your right to use the Service ceases immediately. We will retain your data for 30 days to allow export, after which it will be permanently deleted in accordance with our Privacy Policy.",
    ],
  },
  {
    id: "governing-law",
    number: "7",
    title: "Governing Law & Disputes",
    body: [
      "These Terms are governed by and construed in accordance with applicable law. Any disputes arising under or in connection with these Terms shall first be attempted to be resolved through good-faith negotiation.",
      "If a dispute cannot be resolved informally within 30 days, both parties agree to submit to binding arbitration. Class action lawsuits and class-wide arbitration are expressly waived.",
      "If any provision of these Terms is found to be unenforceable, the remaining provisions will continue in full force and effect.",
    ],
  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function Section({ section }) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-80px 0px" });

  return (
    <motion.section
      ref={ref}
      id={section.id}
      initial={{ opacity: 0, y: 32 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.55, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
      className="scroll-mt-36"
    >
      <div className="flex items-baseline gap-3 mb-4">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-xs font-black text-indigo-600 ring-1 ring-indigo-100">
          {section.number}
        </span>
        <h2 className="text-xl font-bold tracking-tight text-slate-900">
          {section.title}
        </h2>
      </div>
      <div className="ml-11 flex flex-col gap-4">
        {section.body.map((para, i) => (
          <p key={i} className="text-slate-600 leading-relaxed text-[15px]">
            {para}
          </p>
        ))}
      </div>
    </motion.section>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TermsPage() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 200, damping: 30 });

  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 80);
    window.addEventListener("scroll", handler, { passive: true });
    return () => window.removeEventListener("scroll", handler);
  }, []);

  return (
    <>
      {/* ── Scroll progress bar ─────────────────────────────────────── */}
      <motion.div
        className="fixed top-0 left-0 right-0 z-[60] h-[3px] origin-left bg-gradient-to-r from-indigo-500 via-blue-500 to-cyan-400"
        style={{ scaleX }}
      />

      {/* ── Sticky glassmorphism document header ────────────────────── */}
      <div
        className={`sticky top-16 z-40 transition-all duration-500 ${
          scrolled
            ? "bg-white/80 backdrop-blur-xl border-b border-slate-200/60 shadow-sm py-3"
            : "bg-transparent py-6"
        }`}
      >
        <div className="max-w-3xl mx-auto px-6">
          <p className="font-semibold uppercase tracking-widest text-indigo-600 text-xs">
            Legal
          </p>
          <h1
            className={`font-black tracking-tight text-slate-900 leading-tight transition-all duration-300 ${
              scrolled ? "text-xl" : "text-3xl"
            }`}
          >
            Terms of Service
          </h1>
        </div>
      </div>

      {/* ── Main content ────────────────────────────────────────────── */}
      <main className="min-h-screen bg-slate-50/40">
        <div className="max-w-3xl mx-auto px-6 pb-24 pt-10">

          {/* Intro card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="mb-10 rounded-2xl border border-indigo-100 bg-indigo-50/60 px-6 py-5"
          >
            <p className="text-sm font-medium text-indigo-800 leading-relaxed">
              <span className="font-black">Effective date: January 1, 2026.</span>
              {" "}Please read these Terms carefully before using CampaignPulse. By accessing or using
              our platform you agree to be bound by the following conditions.
            </p>
          </motion.div>

          {/* Quick-nav */}
          <motion.nav
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.4 }}
            className="mb-12 flex flex-wrap gap-2"
            aria-label="Jump to section"
          >
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-600 transition-all duration-200 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600"
              >
                {s.number}. {s.title}
              </a>
            ))}
          </motion.nav>

          {/* Sections */}
          <div className="flex flex-col gap-12 divide-y divide-slate-200">
            {sections.map((section, i) => (
              <div key={section.id} className={i > 0 ? "pt-10" : ""}>
                <Section section={section} />
              </div>
            ))}
          </div>

          {/* Footer note */}
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="mt-16 rounded-2xl border border-slate-200 bg-white px-6 py-5 text-center"
          >
            <p className="text-sm text-slate-500">
              Questions about these terms?{" "}
              <a
                href="mailto:legal@campaignpulse.io"
                className="font-semibold text-indigo-600 hover:underline"
              >
                legal@campaignpulse.io
              </a>
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Last updated: 1 January 2026 · CampaignPulse Inc.
            </p>
          </motion.div>
        </div>
      </main>
    </>
  );
}
