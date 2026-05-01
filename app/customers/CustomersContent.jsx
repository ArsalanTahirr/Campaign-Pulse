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

const stats = [
  { label: "2,400+", desc: "Active Senders" },
  { label: "94.7%", desc: "Avg Inbox Rate" },
  { label: "3.2M", desc: "Emails Sent" }
];

const useCases = [
  {
    id: "agencies",
    label: "Marketing Agencies",
    headline: "How Growth Agencies Scale Outreach Without Burnout",
    subtitle: "Managing outreach for 12+ clients used to mean juggling spreadsheets, burning domains, and manually tracking replies.",
    outcomes: [
      { value: "↑ 340%", label: "reply rate" },
      { value: "↓ 80%", label: "domain burnout" },
      { value: "12", label: "clients managed" }
    ],
    body: "With CampaignPulse, one agency we work with now manages 12+ concurrent campaigns without domain burnout. Their reply rates climbed 340% in the first three months. The AI warmup eliminated manual domain setup, and inbox rotation lets them scale horizontally instead of burning through sending domains. Their team went from managing campaigns in Sheets to full automation."
  },
  {
    id: "founders",
    label: "SaaS Founders",
    headline: "From 0 to Pipeline: A SaaS Founder's Cold Email Playbook",
    subtitle: "Cold email was intimidating. Most SaaS founders avoid it or try half-hearted campaigns that get instantly blocked.",
    outcomes: [
      { value: "↑ 28%", label: "demo bookings" },
      { value: "4", label: "new enterprise clients" },
      { value: "6-week", label: "ramp time" }
    ],
    body: "A B2B SaaS founder used CampaignPulse to build their first cold email motion. In six weeks, they booked 4 enterprise demos from cold outreach—something they'd never done before. The platform's analytics showed exactly which subject lines and sequences were driving response. Now cold email accounts for 28% of their pipeline. No special tricks—just the right tools and data."
  },
  {
    id: "recruiters",
    label: "Recruiters",
    headline: "Filling Roles 2x Faster with Automated Outreach",
    subtitle: "Recruitment outreach requires volume, speed, and personalization. Manual email isn't cutting it anymore.",
    outcomes: [
      { value: "↑ 55%", label: "response rate" },
      { value: "18", label: "placements in Q1" },
      { value: "3 hrs", label: "saved per day" }
    ],
    body: "A recruiting firm was struggling to fill tech roles. Their old approach: tons of manual email with 8% response rates. They switched to CampaignPulse, set up smart inbox rotation to avoid spam filters, personalized every email using tokens, and let the AI warmup build reputation. Result: 55% response rate, 18 placements in Q1, and 3 hours of manual work saved every single day."
  }
];

const testimonials = [
  {
    name: "Sarah Chen",
    role: "Head of Growth",
    company: "Velocity Agency",
    quote: "CampaignPulse's warmup feature alone paid for itself in the first week. We went from 14% inbox rate to 91% in 21 days.",
    metric: "91% inbox rate",
    initials: "SC",
    logo: "VA"
  },
  {
    name: "Marcus Reid",
    role: "Founder & CEO",
    company: "LaunchStack SaaS",
    quote: "I was skeptical about AI warmup but the results speak for themselves. Booked 4 enterprise demos in my first campaign.",
    metric: "4 enterprise demos",
    initials: "MR",
    logo: "LS"
  },
  {
    name: "Priya Nair",
    role: "Talent Acquisition Lead",
    company: "HireFlow Recruiting",
    quote: "The inbox rotation feature is a game-changer. No more worrying about daily sending limits killing our momentum.",
    metric: "55% reply rate",
    initials: "PN",
    logo: "HF"
  },
  {
    name: "James Okafor",
    role: "Sales Director",
    company: "Meridian B2B",
    quote: "Finally a cold email tool that doesn't feel like it was built in 2015. The analytics dashboard is genuinely beautiful.",
    metric: "↑ 3x pipeline",
    initials: "JO",
    logo: "M2"
  }
];

const companies = ["VelocityAgency", "LaunchStack", "HireFlow", "Meridian", "NexGen", "PivotCo"];

function AnimatedCounter({ value, duration = 2 }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    let start = 0;
    const increment = value / (duration * 60); // Assuming 60fps
    const interval = setInterval(() => {
      start += increment;
      if (start >= value) {
        setDisplayValue(value);
        clearInterval(interval);
      } else {
        setDisplayValue(Math.floor(start));
      }
    }, 1000 / 60);

    return () => clearInterval(interval);
  }, [value, duration]);

  return displayValue;
}

export default function CustomersContent() {
  const [activeTab, setActiveTab] = useState("agencies");
  const [currentTestimonial, setCurrentTestimonial] = useState(0);
  const [isAutoPlay, setIsAutoPlay] = useState(true);
  const autoPlayRef = useRef(null);

  useEffect(() => {
    if (!isAutoPlay) return;

    autoPlayRef.current = setInterval(() => {
      setCurrentTestimonial((prev) => (prev + 1) % testimonials.length);
    }, 4000);

    return () => clearInterval(autoPlayRef.current);
  }, [isAutoPlay]);

  const nextTestimonial = () => {
    setCurrentTestimonial((prev) => (prev + 1) % testimonials.length);
    setIsAutoPlay(false);
  };

  const prevTestimonial = () => {
    setCurrentTestimonial((prev) => (prev - 1 + testimonials.length) % testimonials.length);
    setIsAutoPlay(false);
  };

  const activeUseCase = useCases.find((uc) => uc.id === activeTab);

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
              Customer Stories
            </motion.p>

            <motion.h1
              variants={fadeUp}
              className="text-5xl md:text-6xl font-bold tracking-tight text-gray-900 mb-6"
            >
              Teams that send smarter with CampaignPulse
            </motion.h1>

            <motion.p
              variants={fadeUp}
              className="text-xl text-gray-600 mb-12 max-w-2xl mx-auto leading-relaxed"
            >
              From solo founders to 50-person agencies — see how teams are hitting the inbox and booking more meetings.
            </motion.p>

            {/* Stats Bar */}
            <motion.div
              variants={fadeUp}
              className="flex flex-col sm:flex-row justify-center gap-8 sm:gap-0 sm:divide-x divide-gray-300"
            >
              {stats.map((stat, i) => (
                <div key={i} className="flex-1">
                  <motion.div
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    transition={{ delay: i * 0.2, duration: 0.6 }}
                  >
                    <p className="text-3xl md:text-4xl font-bold text-indigo-600">
                      <AnimatedCounter value={parseInt(stat.label.replace(/[^\d]/g, ''))} />
                      {stat.label.replace(/[0-9]/g, '')}
                    </p>
                    <p className="text-sm text-gray-600 mt-1">{stat.desc}</p>
                  </motion.div>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Use Case Tabs */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          {/* Tab Navigation */}
          <div className="flex gap-4 mb-12 border-b border-gray-200">
            {useCases.map((useCase) => (
              <button
                key={useCase.id}
                onClick={() => setActiveTab(useCase.id)}
                className={`pb-4 px-4 font-semibold transition ${
                  activeTab === useCase.id
                    ? 'border-b-2 border-indigo-600 text-indigo-600'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {useCase.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="grid grid-cols-1 md:grid-cols-2 gap-12 items-start"
            >
              {/* Left: Text */}
              <div>
                <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
                  {activeUseCase.headline}
                </h2>
                <p className="text-lg text-gray-600 mb-8">{activeUseCase.subtitle}</p>

                {/* Outcomes */}
                <div className="grid grid-cols-3 gap-4 mb-8">
                  {activeUseCase.outcomes.map((outcome, i) => (
                    <div key={i} className="bg-indigo-50 rounded-lg p-4 text-center">
                      <p className="text-2xl font-bold text-indigo-600">{outcome.value}</p>
                      <p className="text-xs text-gray-600 mt-1">{outcome.label}</p>
                    </div>
                  ))}
                </div>

                <p className="text-gray-700 leading-relaxed mb-8">
                  {activeUseCase.body}
                </p>

                <button className="text-indigo-600 font-semibold hover:text-indigo-700 transition cursor-not-allowed opacity-50">
                  Read Full Case Study →
                </button>
              </div>

              {/* Right: Mock Dashboard */}
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl border border-gray-200 p-8 h-96 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-16 h-16 bg-indigo-200 rounded-full mx-auto mb-4 flex items-center justify-center">
                    <svg className="w-8 h-8 text-indigo-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <p className="text-gray-600 font-semibold">Live Campaign Analytics</p>
                  <p className="text-sm text-gray-500 mt-2">Real-time metrics for {activeUseCase.label}</p>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>
      </section>

      {/* Testimonial Slider */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gray-50">
        <div className="max-w-3xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            {/* Quote */}
            <div
              className="text-center mb-8"
              onMouseEnter={() => setIsAutoPlay(false)}
              onMouseLeave={() => setIsAutoPlay(true)}
              aria-live="polite"
            >
              <p className="text-6xl text-indigo-100 font-serif mb-6">"</p>

              <AnimatePresence mode="wait">
                <motion.blockquote
                  key={currentTestimonial}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.5, ease: 'easeOut' }}
                  className="text-2xl md:text-3xl font-semibold text-gray-900 mb-8 leading-relaxed"
                >
                  {testimonials[currentTestimonial].quote}
                </motion.blockquote>
              </AnimatePresence>

              {/* Author */}
              <AnimatePresence mode="wait">
                <motion.div
                  key={`author-${currentTestimonial}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.5 }}
                  className="flex flex-col items-center"
                >
                  <div className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center text-white font-bold text-lg mb-4">
                    {testimonials[currentTestimonial].initials}
                  </div>

                  <div>
                    <p className="font-semibold text-gray-900">
                      {testimonials[currentTestimonial].name}
                    </p>
                    <p className="text-sm text-gray-600">
                      {testimonials[currentTestimonial].role}, {testimonials[currentTestimonial].company}
                    </p>
                  </div>

                  <div className="mt-4 bg-indigo-50 px-4 py-2 rounded-full">
                    <p className="text-sm font-semibold text-indigo-600">
                      {testimonials[currentTestimonial].metric}
                    </p>
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>

            {/* Navigation Dots */}
            <div className="flex justify-center gap-3 mb-8">
              {testimonials.map((_, i) => (
                <motion.button
                  key={i}
                  onClick={() => {
                    setCurrentTestimonial(i);
                    setIsAutoPlay(false);
                  }}
                  layoutId={i === currentTestimonial ? "active-dot" : undefined}
                  className={`rounded-full transition ${
                    i === currentTestimonial
                      ? 'bg-indigo-600 w-6 h-2'
                      : 'bg-gray-300 w-2 h-2 hover:bg-gray-400'
                  }`}
                />
              ))}
            </div>

            {/* Navigation Arrows */}
            <div className="flex justify-center gap-4">
              <button
                onClick={prevTestimonial}
                className="p-3 rounded-full border border-gray-300 hover:border-indigo-600 hover:text-indigo-600 transition"
                aria-label="Previous testimonial"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                onClick={nextTestimonial}
                className="p-3 rounded-full border border-gray-300 hover:border-indigo-600 hover:text-indigo-600 transition"
                aria-label="Next testimonial"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Logo Garden */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-12"
          >
            <p className="text-gray-600 text-lg font-semibold">Trusted by senders at</p>
          </motion.div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={{
              visible: {
                transition: { staggerChildren: 0.1 }
              }
            }}
            className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8"
          >
            {companies.map((company, i) => (
              <motion.div
                key={i}
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  visible: { opacity: 1, y: 0 }
                }}
                className="flex items-center justify-center p-4 grayscale hover:grayscale-0 transition duration-300 cursor-pointer"
              >
                <div className="font-semibold text-gray-400 hover:text-gray-900 transition text-center text-sm">
                  {company}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-indigo-600 to-purple-600">
        <div className="max-w-2xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
              Ready to become a CampaignPulse success story?
            </h2>
            <Link
              href="/signup"
              className="inline-block px-8 py-4 bg-white text-indigo-600 font-semibold rounded-xl hover:bg-gray-100 transition shadow-lg"
            >
              Start Your Free Trial
            </Link>
          </motion.div>
        </div>
      </section>
    </main>
  );
}
