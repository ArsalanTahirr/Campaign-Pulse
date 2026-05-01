'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';

export default function DemoPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="max-w-2xl mx-auto text-center"
      >
        <div className="mb-8">
          <div className="inline-block px-4 py-2 bg-indigo-100 text-indigo-700 rounded-full text-sm font-semibold mb-6">
            Demo Page
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            Apko kia laga ham yeh bhi banaingai
          </h1>
          
          <p className="text-xl text-gray-600 mb-12 leading-relaxed">
            A quick demo page to showcase that we can build anything you imagine! 🚀
          </p>

          <div className="flex gap-4 justify-center">
            <Link
              href="/features"
              className="px-8 py-4 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-500/30"
            >
              Back to Features
            </Link>
            <Link
              href="/"
              className="px-8 py-4 border-2 border-indigo-600 text-indigo-600 font-semibold rounded-xl hover:bg-indigo-50 transition"
            >
              Go Home
            </Link>
          </div>
        </div>
      </motion.div>
    </main>
  );
}
