'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import Link from 'next/link';

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] } }
};

const stagger = {
  visible: { transition: { staggerChildren: 0.12 } }
};

const CheckIcon = () => (
  <svg className="w-5 h-5 text-green-600 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
  </svg>
);

const CrossIcon = () => (
  <svg className="w-5 h-5 text-gray-300 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
  </svg>
);

const faqItems = [
  {
    question: "Can I switch plans at any time?",
    answer: "Yes! You can upgrade or downgrade your plan anytime from your account settings. Changes take effect on your next billing cycle."
  },
  {
    question: "What counts as a 'connected inbox'?",
    answer: "A connected inbox is any email address that you've authenticated in CampaignPulse using Gmail, Outlook, or your SMTP credentials. Each inbox can send independently or as part of rotation."
  },
  {
    question: "Do you offer refunds?",
    answer: "We offer a 14-day money-back guarantee on all paid plans. If you're not satisfied, simply reach out to our support team within 14 days of your first charge."
  },
  {
    question: "Is the API available on the Free plan?",
    answer: "No, the API is available starting with the Pro plan at 100k requests/month. Enterprise customers get unlimited API requests with custom rate limits."
  },
  {
    question: "What is the Academic Edition badge?",
    answer: "The Academic Edition highlight on the Pro plan is intended to showcase the platform's full feature set during university project evaluations. It carries all standard Pro features with no academic-specific restrictions."
  }
];

const comparisonRows = [
  {
    group: "Sending & Inboxes",
    rows: [
      { feature: "Connected Inboxes", free: "1", pro: "10", enterprise: "Unlimited" },
      { feature: "Monthly Email Volume", free: "500", pro: "25,000", enterprise: "Unlimited" },
      { feature: "Inbox Rotation", free: false, pro: true, enterprise: true }
    ]
  },
  {
    group: "AI & Warmup",
    rows: [
      { feature: "AI Warmup", free: "Basic", pro: "Advanced", enterprise: "Custom" },
      { feature: "Warmup Duration", free: "7 days", pro: "21 days", enterprise: "Custom" },
      { feature: "Dedicated IP Warming", free: false, pro: false, enterprise: true }
    ]
  },
  {
    group: "Analytics & Testing",
    rows: [
      { feature: "Campaign Analytics", free: "30-day", pro: "Unlimited", enterprise: "Unlimited" },
      { feature: "A/B Testing", free: false, pro: true, enterprise: true },
      { feature: "Custom Reports", free: false, pro: false, enterprise: true }
    ]
  },
  {
    group: "Platform & Support",
    rows: [
      { feature: "API Access", free: false, pro: "100k req/mo", enterprise: "Unlimited" },
      { feature: "Team Seats", free: "1", pro: "5", enterprise: "Unlimited" },
      { feature: "Support", free: "Community", pro: "Priority", enterprise: "Dedicated" },
      { feature: "SLA", free: false, pro: false, enterprise: "99.9%" },
      { feature: "White-Label", free: false, pro: false, enterprise: true }
    ]
  }
];

export default function PricingContent() {
  const [isAnnual, setIsAnnual] = useState(false);
  const [expandedFaq, setExpandedFaq] = useState(null);

  const proPrice = isAnnual ? 78 : 97;
  const savingsLabel = isAnnual ? "Save 20%" : "";

  return (
    <main className="min-h-screen bg-white">
      {/* Hero Section */}
      <section className="pt-32 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial="hidden"
            animate="visible"
            variants={stagger}
          >
            <motion.p
              variants={fadeUp}
              className="text-xs font-semibold uppercase tracking-widest text-indigo-600 mb-4"
            >
              Pricing
            </motion.p>

            <motion.h1
              variants={fadeUp}
              className="text-5xl md:text-6xl font-bold tracking-tight text-gray-900 mb-6"
            >
              Simple, transparent pricing
            </motion.h1>

            <motion.p
              variants={fadeUp}
              className="text-xl text-gray-600 mb-8"
            >
              Choose the plan that fits your sending volume and growth trajectory.
            </motion.p>

            {/* Toggle */}
            <motion.div variants={fadeUp} className="flex justify-center mb-12">
              <div className="inline-flex p-1 bg-gray-100 rounded-full">
                <button
                  onClick={() => setIsAnnual(false)}
                  className={`px-6 py-2 rounded-full font-semibold transition ${
                    !isAnnual
                      ? 'bg-white text-indigo-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Monthly
                </button>
                <button
                  onClick={() => setIsAnnual(true)}
                  className={`px-6 py-2 rounded-full font-semibold transition ${
                    isAnnual
                      ? 'bg-white text-indigo-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Annual
                </button>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={stagger}
            className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch"
          >
            {/* Free Plan */}
            <motion.div
              variants={fadeUp}
              className="bg-white border border-gray-200 rounded-2xl p-8 flex flex-col"
            >
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-gray-900">Free</h3>
                <p className="text-gray-600 text-sm mt-1">Perfect for testing the waters</p>
              </div>

              <div className="mb-8">
                <div className="text-4xl font-bold text-gray-900">$0<span className="text-lg text-gray-600">/mo</span></div>
              </div>

              <button className="w-full py-3 border-2 border-indigo-600 text-indigo-600 font-semibold rounded-lg hover:bg-indigo-50 transition mb-8">
                Get Started Free
              </button>

              <div className="space-y-4 flex-grow">
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">1 connected inbox</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">500 emails/month</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Basic warmup (7-day)</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Campaign analytics (30-day retention)</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Community support</span>
                </div>
                <div className="flex gap-3">
                  <CrossIcon />
                  <span className="text-gray-400">Inbox rotation</span>
                </div>
                <div className="flex gap-3">
                  <CrossIcon />
                  <span className="text-gray-400">A/B testing</span>
                </div>
                <div className="flex gap-3">
                  <CrossIcon />
                  <span className="text-gray-400">API access</span>
                </div>
              </div>
            </motion.div>

            {/* Pro Plan (Featured) */}
            <motion.div
              variants={fadeUp}
              className="md:scale-105 bg-gradient-to-b from-indigo-50 to-white border-2 border-indigo-500 rounded-2xl p-8 flex flex-col relative shadow-2xl"
            >
              {/* Badges */}
              <div className="absolute -top-4 right-8 flex flex-col gap-2">
                <div className="bg-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-full whitespace-nowrap">
                  MOST POPULAR
                </div>
                <div className="bg-amber-100 text-amber-800 text-xs font-semibold px-3 py-1 rounded-full border border-amber-300 whitespace-nowrap relative group cursor-help">
                  🎓 Academic Edition
                  <div className="absolute bottom-full right-0 mb-2 w-48 bg-gray-900 text-white text-xs p-2 rounded opacity-0 group-hover:opacity-100 transition pointer-events-none z-50">
                    Highlighted for university project evaluation
                  </div>
                </div>
              </div>

              <div className="mb-6 pt-6">
                <h3 className="text-2xl font-bold text-gray-900">Pro</h3>
                <p className="text-gray-600 text-sm mt-1">For serious senders and growing teams</p>
              </div>

              <div className="mb-2">
                <div className="text-4xl font-bold text-gray-900">${proPrice}<span className="text-lg text-gray-600">/mo</span></div>
              </div>

              {isAnnual && (
                <p className="text-sm text-green-600 font-semibold mb-6">Save 20% annually</p>
              )}

              <button className="w-full py-3 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition mb-2">
                Start Pro Trial
              </button>
              <p className="text-xs text-center text-gray-600 mb-8">14-day free trial · No credit card required</p>

              <div className="space-y-4 flex-grow">
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">10 connected inboxes</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">25,000 emails/month</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Advanced AI warmup (21-day)</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Smart inbox rotation</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Full campaign analytics (unlimited retention)</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">A/B subject line testing</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Personalization tokens</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">API access (100k req/mo)</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Priority email support</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Team seats (up to 5)</span>
                </div>
              </div>
            </motion.div>

            {/* Enterprise Plan */}
            <motion.div
              variants={fadeUp}
              className="bg-white border border-gray-200 rounded-2xl p-8 flex flex-col"
            >
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-gray-900">Enterprise</h3>
                <p className="text-gray-600 text-sm mt-1">For agencies and high-volume senders</p>
              </div>

              <div className="mb-8">
                <div className="text-4xl font-bold text-gray-900">Custom</div>
                <p className="text-gray-600 text-sm mt-1">Let's talk pricing</p>
              </div>

              <button className="w-full py-3 border-2 border-gray-200 text-gray-700 font-semibold rounded-lg hover:border-gray-300 transition mb-8">
                Contact Sales
              </button>

              <div className="space-y-4 flex-grow">
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Unlimited inboxes</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Unlimited email volume</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Dedicated IP warming</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Custom AI warmup schedules</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">White-label dashboard</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">SLA guarantee (99.9% uptime)</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Dedicated account manager</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">Custom integrations & webhooks</span>
                </div>
                <div className="flex gap-3">
                  <CheckIcon />
                  <span className="text-gray-700">SSO / SAML support</span>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Comparison Table */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-bold text-gray-900 mb-12">Detailed Comparison</h2>

            <div className="bg-white rounded-2xl border border-gray-200 overflow-x-auto">
              <table className="w-full">
                <thead className="border-b border-gray-200 bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Feature</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Free</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-indigo-600 bg-indigo-50/30">Pro</th>
                    <th className="px-6 py-4 text-left text-sm font-semibold text-gray-900">Enterprise</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map((group, groupIdx) => (
                    <React.Fragment key={groupIdx}>
                      <tr className="border-b border-gray-200 bg-gray-50">
                        <td colSpan="4" className="px-6 py-3">
                          <p className="text-xs font-semibold uppercase tracking-widest text-gray-700">{group.group}</p>
                        </td>
                      </tr>
                      {group.rows.map((row, rowIdx) => (
                        <tr key={rowIdx} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="px-6 py-4 text-sm font-medium text-gray-900">{row.feature}</td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {typeof row.free === 'boolean' ? (
                              row.free ? <CheckIcon /> : <CrossIcon />
                            ) : (
                              row.free
                            )}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900 bg-indigo-50/30">
                            {typeof row.pro === 'boolean' ? (
                              row.pro ? <CheckIcon /> : <CrossIcon />
                            ) : (
                              row.pro
                            )}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {typeof row.enterprise === 'boolean' ? (
                              row.enterprise ? <CheckIcon /> : <CrossIcon />
                            ) : (
                              row.enterprise
                            )}
                          </td>
                        </tr>
                      ))}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-bold text-gray-900 mb-12 text-center">Frequently Asked Questions</h2>

            <div className="space-y-4">
              {faqItems.map((item, idx) => (
                <motion.div
                  key={idx}
                  className="border border-gray-200 rounded-xl overflow-hidden"
                  initial={false}
                >
                  <button
                    onClick={() => setExpandedFaq(expandedFaq === idx ? null : idx)}
                    className="w-full px-6 py-4 flex justify-between items-center hover:bg-gray-50 transition"
                  >
                    <span className="font-semibold text-gray-900 text-left">{item.question}</span>
                    <svg
                      className={`w-5 h-5 text-gray-600 transition-transform ${
                        expandedFaq === idx ? 'rotate-180' : ''
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                    </svg>
                  </button>

                  <AnimatePresence>
                    {expandedFaq === idx && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="border-t border-gray-200 bg-gray-50"
                      >
                        <p className="px-6 py-4 text-gray-600">{item.answer}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>
    </main>
  );
}
