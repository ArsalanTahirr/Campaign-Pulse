"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Users, ChevronDown, AlertCircle } from "lucide-react";

const GENDER_OPTIONS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "prefer_not", label: "Prefer not to say" }
];

export default function GenderSelect({
  value,
  onChange,
  onBlur,
  error,
  id = "gender"
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  const triggerRef = useRef(null);

  // Get label for selected value
  const getLabel = (val) => {
    if (!val) return "Select your gender";
    return GENDER_OPTIONS.find(opt => opt.value === val)?.label || "Select your gender";
  };

  // Handle option selection
  const handleSelectOption = (optionValue) => {
    onChange(optionValue);
    setIsOpen(false);
  };

  // Handle trigger blur
  const handleTriggerBlur = () => {
    setTimeout(() => {
      if (containerRef.current && !containerRef.current.contains(document.activeElement)) {
        setIsOpen(false);
        if (onBlur) onBlur();
      }
    }, 100);
  };

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  return (
    <div>
      <div className="relative" ref={containerRef}>
        {/* Trigger Button */}
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          onBlur={handleTriggerBlur}
          className={`h-12 w-full rounded-xl px-4 py-3 flex items-center justify-between gap-3 transition duration-200 ${
            error
              ? "border border-red-500 bg-red-50/70 backdrop-blur-md text-red-900 focus:border-red-500 focus:outline-none focus:ring-4 focus:ring-red-500/20"
              : "border border-slate-200/70 bg-white/70 backdrop-blur-md text-slate-900 shadow-sm hover:bg-white/80 focus:border-brand-500 focus:outline-none focus:ring-4 focus:ring-brand-500/20 focus:shadow-glow"
          }`}
        >
          <div className="flex items-center gap-3 flex-1">
            <Users className="h-4 w-4 flex-shrink-0 text-slate-400" strokeWidth={2} />
            <span className={value ? "text-slate-900 font-medium" : "text-slate-400"}>
              {getLabel(value)}
            </span>
          </div>
          <ChevronDown
            className={`h-4 w-4 flex-shrink-0 text-slate-400 transition-transform duration-200 ${
              isOpen ? "rotate-180" : ""
            }`}
            strokeWidth={2}
          />
        </button>

        {/* Dropdown Menu */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -8 }}
              transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
              className="absolute top-full z-50 mt-2 w-full rounded-2xl border border-slate-200/70 bg-white/95 backdrop-blur-xl shadow-lg overflow-hidden"
            >
              <div className="py-2">
                {GENDER_OPTIONS.map((option) => {
                  const isSelected = value === option.value;
                  return (
                    <motion.button
                      key={option.value}
                      type="button"
                      onClick={() => handleSelectOption(option.value)}
                      whileHover={{ x: 4 }}
                      className={`w-full px-4 py-3 text-sm font-medium text-left transition-colors duration-150 flex items-center gap-3 ${
                        isSelected
                          ? "bg-gradient-to-r from-brand-50 to-brand-50/50 text-brand-900 border-l-2 border-brand-500"
                          : "text-slate-700 hover:bg-slate-100/50"
                      }`}
                    >
                      <span className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                        isSelected
                          ? "border-brand-500 bg-brand-500"
                          : "border-slate-300 group-hover:border-slate-400"
                      }`}>
                        {isSelected && (
                          <svg
                            className="w-3 h-3 text-white"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth={3}
                          >
                            <path d="M20 6L9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                      </span>
                      {option.label}
                    </motion.button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Error message */}
      <div
        className={`grid transition-all duration-300 ease-in-out ${
          error ? "grid-rows-[1fr] opacity-100 mt-1.5" : "grid-rows-[0fr] opacity-0"
        }`}
      >
        <div className="overflow-hidden">
          <p className="text-xs text-red-600">{error}</p>
        </div>
      </div>
    </div>
  );
}
