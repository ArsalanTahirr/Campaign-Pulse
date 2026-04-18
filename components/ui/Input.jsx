"use client";

import { motion } from "framer-motion";
import { useId } from "react";

export default function Input({ label, type = "text", placeholder = " " }) {
  const id = useId();

  return (
    <motion.div
      whileFocus={{ scale: 1.01 }}
      className="relative"
      transition={{ duration: 0.2 }}
    >
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        className="peer h-12 w-full rounded-xl border border-slate-200 bg-white px-4 text-sm text-slate-900 outline-none transition duration-200 placeholder:text-transparent focus:border-brand-500 focus:shadow-glow"
      />
      <label
        htmlFor={id}
        className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 bg-white px-1 text-sm text-slate-500 transition-all duration-200 peer-focus:top-0 peer-focus:text-xs peer-focus:text-brand-600 peer-[:not(:placeholder-shown)]:top-0 peer-[:not(:placeholder-shown)]:text-xs"
      >
        {label}
      </label>
    </motion.div>
  );
}
