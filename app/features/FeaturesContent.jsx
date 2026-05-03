'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

const fadeUp = {
  hidden: { opacity: 0, y: 32 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] } }
};

const stagger = {
  visible: { transition: { staggerChildren: 0.12 } }
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2,
    }
  }
};

const cardVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: (i) => ({
    opacity: 1, y: 0,
    transition: { delay: i * 0.15, duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }
  })
};

// SVG Icons
const FlameIcon = () => (
  <svg className="w-12 h-12 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z" />
  </svg>
);

const RotateIcon = () => (
  <svg className="w-12 h-12 text-purple-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M15.55 5.55L11 1v3.07C7.06 4.56 4 7.72 4 11.5c0 .33.02.66.07 1h2.02c-.05-.34-.07-.67-.07-1 0-2.64 2.05-4.78 4.61-4.93v3.43h4.92zm2.38 3.4h-2.02c.05.34.07.67.07 1 0 2.64-2.05 4.78-4.61 4.93v-3.43H7.45v8.95h8.95v-3.07c3.94-1.49 7-4.65 7-8.38 0-.33-.02-.66-.07-1z" />
  </svg>
);

const AnalyticsIcon = () => (
  <svg className="w-12 h-12 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z" />
  </svg>
);

const CodeIcon = () => (
  <svg className="w-12 h-12 text-white" fill="currentColor" viewBox="0 0 24 24">
    <path d="M9.4 16.6L4.8 12l4.6-4.6L6.6 6 0 12l6.6 6 2.8-2.4zm5.2 0l4.6-4.6-4.6-4.6 2.8-2.8L24 12l-6.6 6 2.8 2.4-2.8 2.8z" />
  </svg>
);

const ShieldIcon = () => (
  <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z" />
  </svg>
);

const FlaskIcon = () => (
  <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M9 2c-1.105 0-2 .895-2 2v2H5c-1.105 0-2 .895-2 2v2c0 1.105.895 2 2 2h.105C5.57 14.211 8.055 17 11 17h2c2.945 0 5.43-2.789 5.895-7H19c1.105 0 2-.895 2-2V8c0-1.105-.895-2-2-2h-2V4c0-1.105-.895-2-2-2H9z" />
  </svg>
);

const UserIcon = () => (
  <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
  </svg>
);

const UsersIcon = () => (
  <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z" />
  </svg>
);

const LinkIcon = () => (
  <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z" />
  </svg>
);

const LockIcon = () => (
  <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
    <path d="M18 8h-1V6c0-2.76-2.24-5-5-5s-5 2.24-5 5v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zM9 6c0-1.66 1.34-3 3-3s3 1.34 3 3v2H9V6zm9 14H6V10h12v10zm-6-3c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2z" />
  </svg>
);

const secondaryFeatures = [
  { icon: ShieldIcon, title: "Deliverability Monitoring", desc: "Track sender reputation across 50+ ISPs in real-time" },
  { icon: FlaskIcon, title: "A/B Subject Line Testing", desc: "Statistically significant split testing built-in" },
  { icon: UserIcon, title: "Personalization Tokens", desc: "Dynamic content insertion based on lead data" },
  { icon: UsersIcon, title: "Team Collaboration", desc: "Invite team members with granular permissions" },
  { icon: LinkIcon, title: "CRM Integrations", desc: "Native integrations with Salesforce, HubSpot, Pipedrive" },
  { icon: LockIcon, title: "GDPR Compliance", desc: "SOC 2 Type II certified, GDPR and CCPA ready" }
];

export default function FeaturesContent() {
  const [inView, setInView] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.2 }
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

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
              Platform Features
            </motion.p>

            <motion.h1
              variants={fadeUp}
              className="text-5xl md:text-6xl font-bold tracking-tight text-gray-900 mb-6"
            >
              Everything you need to land in the inbox
            </motion.h1>

            <motion.p
              variants={fadeUp}
              className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto leading-relaxed"
            >
              CampaignPulse combines AI-powered warmup, intelligent inbox rotation, and real-time analytics into one seamless platform.
            </motion.p>

            <motion.div
              variants={fadeUp}
              className="flex flex-col sm:flex-row gap-4 justify-center"
            >
              <Link
                href="/signup"
                className="px-8 py-4 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/30"
              >
                Start Free Trial →
              </Link>
              <Link href="/demo" className="px-8 py-4 border-2 border-indigo-600 text-indigo-600 font-semibold rounded-xl hover:bg-indigo-50 transition">
                Watch Demo
              </Link>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Bento Grid */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50">
        <div className="max-w-7xl mx-auto">
          <motion.div
            ref={ref}
            initial="hidden"
            animate={inView ? "visible" : "hidden"}
            variants={containerVariants}
            className="grid grid-cols-12 gap-6 auto-rows-[300px]"
          >
            {/* Card 1 - AI Warmup (large) */}
            <motion.div
              custom={0}
              variants={cardVariants}
              whileHover={{ y: -8, boxShadow: '0 20px 40px rgba(79, 70, 229, 0.15)' }}
              className="col-span-12 md:col-span-7 md:row-span-2 bg-white rounded-2xl border border-gray-200 p-8 hover:border-indigo-300 transition cursor-pointer"
            >
              <div className="h-full flex flex-col justify-between">
                <div>
                  <div className="mb-6">
                    <FlameIcon />
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">AI-Powered Email Warmup</h3>
                  <p className="text-gray-600 mb-6">
                    Our proprietary AI gradually increases your sending volume, mimicking human behavior to build domain reputation before your first campaign goes live.
                  </p>
                </div>

                {/* Stats Row */}
                <div className="flex gap-6 mb-8 py-6 border-t border-gray-200">
                  <div>
                    <p className="text-3xl font-bold text-indigo-600">14</p>
                    <p className="text-sm text-gray-600">day warmup</p>
                  </div>
                  <div>
                    <p className="text-3xl font-bold text-green-600">98.2%</p>
                    <p className="text-sm text-gray-600">inbox rate</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-gray-900">0</p>
                    <p className="text-sm text-gray-600">manual setup</p>
                  </div>
                </div>

                {/* Animated Chart */}
                <div className="h-20 bg-indigo-50 rounded-xl flex items-end justify-around p-4">
                  {[0.3, 0.5, 0.7, 0.9, 0.8, 0.95, 1].map((height, i) => (
                    <motion.div
                      key={i}
                      className="bg-indigo-600 rounded-sm"
                      style={{ width: '8px', height: `${height * 100}%` }}
                      initial={{ height: 0 }}
                      animate={{ height: `${height * 100}%` }}
                      transition={{ duration: 0.8, delay: i * 0.1 }}
                    />
                  ))}
                </div>
              </div>
            </motion.div>

            {/* Card 2 - Inbox Rotation */}
            <motion.div
              custom={1}
              variants={cardVariants}
              whileHover={{ y: -8, boxShadow: '0 20px 40px rgba(79, 70, 229, 0.15)' }}
              className="col-span-12 md:col-span-5 bg-white rounded-2xl border border-gray-200 p-8 pb-20 overflow-hidden hover:border-purple-300 transition cursor-pointer"
            >
              <RotateIcon />
              <h3 className="text-xl font-bold text-gray-900 my-4">Smart Inbox Rotation</h3>
              <p className="text-gray-600 mb-6">
                Distribute sends across multiple inboxes automatically. CampaignPulse intelligently balances load to protect sender reputation.
              </p>
              <div className="space-y-2">
                {['inbox@domain1.com', 'sales@domain2.com', 'hello@domain3.com'].map((email, i) => (
                  <motion.div
                    key={i}
                    className="inline-block px-3 py-1 rounded-full bg-purple-100 text-purple-700 text-sm font-medium"
                    animate={{ rotate: [0, 5, -5, 0] }}
                    transition={{ duration: 4, delay: i * 0.3, repeat: Infinity }}
                  >
                    {email}
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Card 3 - Analytics */}
            <motion.div
              custom={2}
              variants={cardVariants}
              whileHover={{ y: -8, boxShadow: '0 20px 40px rgba(79, 70, 229, 0.15)' }}
              className="col-span-12 md:col-span-7 bg-white rounded-2xl border border-gray-200 p-8 hover:border-indigo-300 transition cursor-pointer"
            >
              <AnalyticsIcon />
              <h3 className="text-xl font-bold text-gray-900 my-4">Real-Time Campaign Analytics</h3>
              <p className="text-gray-600 mb-6">
                Track opens, clicks, replies, and bounce rates with a live dashboard. A/B test subject lines with statistical confidence.
              </p>
              <div className="flex gap-4">
                <div>
                  <p className="text-2xl font-bold text-indigo-600">47%</p>
                  <p className="text-sm text-gray-600">avg open rate</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-indigo-600">12%</p>
                  <p className="text-sm text-gray-600">reply rate</p>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Secondary Features Grid */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: "-100px" }}
            variants={stagger}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8"
          >
            {secondaryFeatures.map((feature, i) => (
              <motion.div
                key={i}
                custom={i}
                variants={cardVariants}
                whileHover={{ y: -4, borderColor: '#4F46E5' }}
                className="p-6 border border-gray-200 rounded-2xl hover:shadow-md transition"
              >
                <div className="mb-4">
                  <feature.icon />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-600 text-sm">{feature.desc}</p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-indigo-600 to-purple-600">
        <div className="max-w-2xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Ready to transform your cold email strategy?
            </h2>
            <Link
              href="/signup"
              className="inline-block px-8 py-4 bg-white text-indigo-600 font-semibold rounded-xl hover:bg-gray-100 transition shadow-lg"
            >
              Start Free — No Credit Card
            </Link>
          </motion.div>
        </div>
      </section>
    </main>
  );
}
