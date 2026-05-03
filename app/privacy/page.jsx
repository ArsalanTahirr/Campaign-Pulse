'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.2,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 py-20 px-6">
      <div className="max-w-3xl mx-auto">
        {/* Back Button */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.5 }}>
          <Link href="/" className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-8 group">
            <ArrowLeft className="w-4 h-4 group-hover:scale-105 transition-transform" />
            Back to Home
          </Link>
        </motion.div>

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="mb-12">
          <h1 className="text-5xl font-bold bg-gradient-to-r from-white via-indigo-200 to-white text-transparent bg-clip-text mb-4">
            Privacy Policy
          </h1>
        </motion.div>

        {/* Glassmorphism Container */}
        <motion.div
          className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-8"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <motion.div variants={containerVariants} initial="hidden" animate="visible" className="space-y-8">
            {/* Introduction */}
            <motion.section variants={itemVariants}>
              <h2 className="text-xl font-semibold text-white mb-2">Introduction</h2>
              <p className="text-gray-400 leading-relaxed">
                We are committed to protecting your privacy and ensuring you have a positive experience on CampaignPulse. This Privacy Policy explains our practices regarding data collection and usage.
              </p>
            </motion.section>

            {/* Data Collection & Usage */}
            <motion.section variants={itemVariants}>
              <h2 className="text-xl font-semibold text-white mb-2">Data Collection & Usage</h2>
              <p className="text-gray-400 leading-relaxed">
                CampaignPulse processes lead data strictly for the purpose of email campaign analytics and intelligent inbox rotation logic. Your data is used exclusively for:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-2 mt-3 text-gray-400">
                <li>Campaign performance analytics</li>
                <li>Email rotation optimization</li>
                <li>Deliverability tracking</li>
                <li>Service improvement</li>
              </ul>
              <p className="text-gray-400 leading-relaxed mt-3">
                <strong>We do not resell, misuse, or share your data with third parties.</strong>
              </p>
            </motion.section>

            {/* Security */}
            <motion.section variants={itemVariants}>
              <h2 className="text-xl font-semibold text-white mb-2">Security</h2>
              <p className="text-gray-400 leading-relaxed">
                All SMTP credentials are encrypted using AES-256 encryption standards. Your data is protected with industry-leading security protocols and stored on secure, managed infrastructure.
              </p>
            </motion.section>

            {/* Team Infinity Note */}
            <motion.section variants={itemVariants}>
              <h2 className="text-xl font-semibold text-white mb-2">About This Project</h2>
              <p className="text-gray-400 leading-relaxed">
                CampaignPulse is developed by Team Infinity at the National University of Computer and Emerging Sciences (NUCES-Khi) as part of a comprehensive database management systems project.
              </p>
            </motion.section>

            {/* Academic Disclaimer */}
            <motion.div variants={itemVariants} className="text-xs text-gray-500 mt-10 border-t border-white/10 pt-6">
              <p>
                This policy is part of a Database Management Systems academic project at NUCES-Khi. No real user data is harvested.
              </p>
            </motion.div>
          </motion.div>
        </motion.div>
      </div>
    </main>
  );
}
