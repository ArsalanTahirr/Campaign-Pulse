'use client';

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

const cardVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: (i) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.15, duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }
  })
};

// Icons
const ChartIcon = () => (
  <svg className="w-12 h-12 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z" />
  </svg>
);

const ShieldCheckIcon = () => (
  <svg className="w-12 h-12 text-green-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 11l-2-2 1.41-1.41L10 9.17l4.59-4.58L16 6l-6 6z" />
  </svg>
);

const CodeIcon = () => (
  <svg className="w-12 h-12 text-purple-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M9.4 16.6L4.8 12l4.6-4.6L6.6 6 0 12l6.6 6 2.8-2.4zm5.2 0l4.6-4.6-4.6-4.6 2.8-2.8L24 12l-6.6 6 2.8 2.4-2.8 2.8z" />
  </svg>
);

const FlaskIcon = () => (
  <svg className="w-12 h-12 text-amber-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M9 2c-1.105 0-2 .895-2 2v2H5c-1.105 0-2 .895-2 2v2c0 1.105.895 2 2 2h.105C5.57 14.211 8.055 17 11 17h2c2.945 0 5.43-2.789 5.895-7H19c1.105 0 2-.895 2-2V8c0-1.105-.895-2-2-2h-2V4c0-1.105-.895-2-2-2H9z" />
  </svg>
);

const RotateIcon = () => (
  <svg className="w-12 h-12 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M15.55 5.55L11 1v3.07C7.06 4.56 4 7.72 4 11.5c0 .33.02.66.07 1h2.02c-.05-.34-.07-.67-.07-1 0-2.64 2.05-4.78 4.61-4.93v3.43h4.92zm2.38 3.4h-2.02c.05.34.07.67.07 1 0 2.64-2.05 4.78-4.61 4.93v-3.43H7.45v8.95h8.95v-3.07c3.94-1.49 7-4.65 7-8.38 0-.33-.02-.66-.07-1z" />
  </svg>
);

const DocumentIcon = () => (
  <svg className="w-12 h-12 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M18,20H6V4H13V9H18V20Z" />
  </svg>
);

const resources = [
  {
    id: 1,
    category: "REPORT",
    categoryColor: "indigo",
    icon: ChartIcon,
    title: "2024 Cold Email Benchmarks Report",
    description: "Analyze open rates, reply rates, and bounce rates across 12 industries. Data compiled from 2.3M sends on the CampaignPulse platform.",
    meta: "Updated Jan 2025 · 18 min read",
    cta: "Download Report →",
    featured: true,
    bgGradient: "from-indigo-50 to-purple-50",
    link: "#"
  },
  {
    id: 2,
    category: "GUIDE",
    categoryColor: "green",
    icon: ShieldCheckIcon,
    title: "The Complete Deliverability Guide",
    description: "Everything you need to know about SPF, DKIM, DMARC, and how inbox providers score your sending reputation.",
    meta: "12 chapters · 45 min read",
    cta: "Read Guide →",
    bgGradient: "from-green-50 to-emerald-50",
    link: "#"
  },
  {
    id: 3,
    category: "DEVELOPER",
    categoryColor: "purple",
    icon: CodeIcon,
    title: "CampaignPulse API Reference",
    description: "Full Swagger/OpenAPI documentation for all endpoints. Authenticate, launch campaigns, and retrieve analytics programmatically.",
    meta: "FastAPI · Auto-generated · Always up to date",
    cta: "Open API Docs →",
    isDark: true,
    link: "/docs",
    newTab: true
  },
  {
    id: 4,
    category: "TOOL",
    categoryColor: "amber",
    icon: FlaskIcon,
    title: "Subject Line Spam Score Checker",
    description: "Paste your subject line and get an instant spam score with actionable suggestions. Powered by CampaignPulse AI.",
    cta: "Try the Tool → (Coming Soon)",
    isComingSoon: true,
    bgGradient: "from-amber-50 to-orange-50",
    link: "#"
  },
  {
    id: 5,
    category: "GUIDE",
    categoryColor: "green",
    icon: RotateIcon,
    title: "Inbox Rotation: A Practical Playbook",
    description: "Step-by-step setup for rotating across multiple inboxes. Includes domain naming conventions and warmup sequencing.",
    meta: "8 min read",
    cta: "Read Guide →",
    link: "#"
  },
  {
    id: 6,
    category: "TEMPLATE",
    categoryColor: "blue",
    icon: DocumentIcon,
    title: "50 Cold Email Templates That Get Replies",
    description: "Swipe-worthy templates for SaaS, agencies, recruiting, and B2B sales. Each template includes subject line + follow-up sequence.",
    cta: "Download Free →",
    link: "#"
  }
];

const categoryColors = {
  indigo: { bg: 'bg-indigo-100', text: 'text-indigo-700' },
  green: { bg: 'bg-green-100', text: 'text-green-700' },
  purple: { bg: 'bg-purple-100', text: 'text-purple-700' },
  amber: { bg: 'bg-amber-100', text: 'text-amber-700' },
  blue: { bg: 'bg-blue-100', text: 'text-blue-700' }
};

export default function ResourcesContent() {
  const [email, setEmail] = useState('');
  const [subscribeStatus, setSubscribeStatus] = useState(null);

  const handleSubscribe = (e) => {
    e.preventDefault();
    if (email) {
      setSubscribeStatus('success');
      setEmail('');
      setTimeout(() => setSubscribeStatus(null), 3000);
    }
  };

  const featuredResources = resources.filter((r) => r.featured);
  const otherResources = resources.filter((r) => !r.featured);

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
              Resources
            </motion.p>

            <motion.h1
              variants={fadeUp}
              className="text-5xl md:text-6xl font-bold tracking-tight text-gray-900 mb-6"
            >
              The Cold Email Knowledge Base
            </motion.h1>

            <motion.p
              variants={fadeUp}
              className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed"
            >
              Guides, benchmarks, and tools to help you master deliverability and run campaigns that actually convert.
            </motion.p>

            {/* Search Bar */}
            <motion.div variants={fadeUp} className="max-w-2xl mx-auto">
              <div className="relative">
                <svg
                  className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                <input
                  type="text"
                  placeholder="Search guides, benchmarks, docs..."
                  className="w-full pl-12 pr-6 py-4 bg-white border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Resource Grid */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={{
              visible: {
                transition: {
                  staggerChildren: 0.15,
                  delayChildren: 0.2,
                }
              }
            }}
            className="space-y-8"
          >
            {/* Featured Card */}
            {featuredResources.map((resource, i) => {
              const Icon = resource.icon;
              const colors = categoryColors[resource.categoryColor];

              return (
                <motion.div
                  key={resource.id}
                  custom={i}
                  variants={cardVariants}
                  whileHover={{ y: -6, boxShadow: '0 20px 40px rgba(79, 70, 229, 0.15)' }}
                  className={`bg-gradient-to-br ${resource.bgGradient} rounded-2xl border border-gray-200 p-8 md:p-12 hover:border-indigo-300 transition cursor-pointer`}
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
                    <div>
                      <div className={`inline-block ${colors.bg} ${colors.text} text-xs font-bold px-3 py-1 rounded-full mb-4`}>
                        {resource.category}
                      </div>
                      <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">
                        {resource.title}
                      </h3>
                      <p className="text-gray-700 mb-6 leading-relaxed">
                        {resource.description}
                      </p>
                      <p className="text-sm text-gray-600 mb-6">{resource.meta}</p>
                      <Link
                        href={resource.link}
                        target={resource.newTab ? "_blank" : undefined}
                        className="inline-flex items-center text-indigo-600 font-semibold hover:text-indigo-700 transition"
                      >
                        {resource.cta}
                      </Link>
                    </div>

                    <div className="flex justify-center items-center">
                      <Icon />
                    </div>
                  </div>
                </motion.div>
              );
            })}

            {/* Other Resources Grid */}
            <motion.div
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              variants={{
                visible: {
                  transition: {
                    staggerChildren: 0.1,
                  }
                }
              }}
            >
              {otherResources.map((resource, i) => {
                const Icon = resource.icon;
                const colors = categoryColors[resource.categoryColor];

                return (
                  <motion.div
                    key={resource.id}
                    custom={i}
                    variants={cardVariants}
                    whileHover={{ y: -6, boxShadow: '0 20px 40px rgba(79, 70, 229, 0.15)' }}
                    className={`${
                      resource.isDark
                        ? 'bg-gray-900 border-gray-800'
                        : `bg-gradient-to-br ${resource.bgGradient || 'from-gray-50 to-white'} border-gray-200`
                    } rounded-2xl border p-8 hover:border-indigo-300 transition cursor-pointer flex flex-col`}
                  >
                    <div className={`inline-block ${colors.bg} ${colors.text} text-xs font-bold px-3 py-1 rounded-full mb-4 w-fit`}>
                      {resource.category}
                    </div>

                    <div className="mb-6">
                      {resource.isDark ? (
                        <div className="text-white/30">
                          <Icon />
                        </div>
                      ) : (
                        <Icon />
                      )}
                    </div>

                    <h3 className={`text-lg md:text-xl font-bold mb-3 ${resource.isDark ? 'text-white' : 'text-gray-900'}`}>
                      {resource.title}
                    </h3>

                    <p className={`${resource.isDark ? 'text-gray-400' : 'text-gray-600'} mb-6 flex-grow`}>
                      {resource.description}
                    </p>

                    {resource.meta && (
                      <p className={`text-xs ${resource.isDark ? 'text-gray-500' : 'text-gray-600'} mb-6`}>
                        {resource.meta}
                      </p>
                    )}

                    <Link
                      href={resource.link}
                      target={resource.newTab ? "_blank" : undefined}
                      onClick={(e) => resource.isComingSoon && e.preventDefault()}
                      className={`inline-flex items-center font-semibold transition ${
                        resource.isDark
                          ? 'text-purple-400 hover:text-purple-300'
                          : 'text-indigo-600 hover:text-indigo-700'
                      } ${resource.isComingSoon ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                    >
                      {resource.cta}
                    </Link>
                  </motion.div>
                );
              })}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Newsletter CTA */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-900 text-white">
        <div className="max-w-2xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl md:text-5xl font-bold mb-4">
              Get deliverability insights in your inbox
            </h2>
            <p className="text-lg text-gray-400 mb-8">
              Join 3,200+ senders. Weekly tips, no spam.
            </p>

            <form onSubmit={handleSubscribe} className="flex flex-col sm:flex-row gap-3 mb-4">
              <input
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="flex-1 px-6 py-4 bg-white/10 border border-white/20 rounded-full text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent backdrop-blur"
              />
              <button
                type="submit"
                className="px-8 py-4 bg-indigo-600 text-white font-semibold rounded-full hover:bg-indigo-700 transition whitespace-nowrap"
              >
                Subscribe
              </button>
            </form>

            <AnimatePresence>
              {subscribeStatus === 'success' && (
                <motion.p
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="text-green-400 text-sm"
                >
                  ✓ Thanks for subscribing! Check your email for confirmation.
                </motion.p>
              )}
            </AnimatePresence>

            <p className="text-xs text-gray-500 mt-4">
              No spam. Unsubscribe anytime.
            </p>
          </motion.div>
        </div>
      </section>
    </main>
  );
}
