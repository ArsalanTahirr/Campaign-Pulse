"use client";

import { motion } from "framer-motion";

const variantStyles = {
  primary:
    "bg-brand-600 text-white shadow-lg shadow-brand-500/30 hover:bg-brand-700",
  secondary:
    "bg-white text-slate-900 border border-slate-200 hover:border-brand-200 hover:bg-brand-50",
  ghost: "bg-transparent text-slate-600 hover:bg-slate-100 hover:text-slate-900"
};

export default function Button({
  children,
  variant = "primary",
  className = "",
  fullWidth = false,
  ...props
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.98 }}
      className={`inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold transition duration-200 ${variantStyles[variant]} ${fullWidth ? "w-full" : ""} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
}
