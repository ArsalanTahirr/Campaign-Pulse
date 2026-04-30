"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";

export default function DatePickerPopover({
  value,
  onChange,
  onBlur,
  error,
  placeholder = "Select your birth date",
  id = "date-picker"
}) {
  const parseDateOnly = (dateValue) => {
    if (typeof dateValue !== "string") return null;
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateValue);
    if (!match) return null;
    const y = Number(match[1]);
    const m = Number(match[2]) - 1;
    const d = Number(match[3]);
    const parsed = new Date(y, m, d);
    if (Number.isNaN(parsed.getTime())) return null;
    if (parsed.getFullYear() !== y || parsed.getMonth() !== m || parsed.getDate() !== d) return null;
    return parsed;
  };

  const toDateOnlyString = (date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
  };

  const [isOpen, setIsOpen] = useState(false);
  const [month, setMonth] = useState(
    value ? (parseDateOnly(value)?.getMonth() ?? new Date().getMonth()) : new Date().getMonth()
  );
  const [year, setYear] = useState(
    value ? (parseDateOnly(value)?.getFullYear() ?? new Date().getFullYear()) : new Date().getFullYear()
  );
  const containerRef = useRef(null);
  const triggerRef = useRef(null);

  // Format date for display
  const formatDate = (dateStr) => {
    if (!dateStr) return placeholder;
    const date = parseDateOnly(dateStr);
    if (!date) return placeholder;
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric"
    });
  };

  // Get days in month
  const getDaysInMonth = (m, y) => new Date(y, m + 1, 0).getDate();

  // Get first day of month (0 = Sunday)
  const getFirstDayOfMonth = (m, y) => new Date(y, m, 1).getDay();

  // Generate calendar days
  const generateCalendarDays = () => {
    const daysInMonth = getDaysInMonth(month, year);
    const firstDay = getFirstDayOfMonth(month, year);
    const days = [];

    // Empty cells for days before month starts
    for (let i = 0; i < firstDay; i++) {
      days.push(null);
    }

    // Days of month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(i);
    }

    return days;
  };

  // Handle date selection
  const handleSelectDate = (day) => {
    const selected = new Date(year, month, day);
    const dateString = toDateOnlyString(selected);
    onChange(dateString);
    setIsOpen(false);
  };

  // Handle Today
  const handleToday = () => {
    const today = new Date();
    const dateString = toDateOnlyString(today);
    onChange(dateString);
    setIsOpen(false);
  };

  // Handle Clear
  const handleClear = () => {
    onChange("");
    setIsOpen(false);
  };

  // Handle month/year change
  const handlePrevMonth = () => {
    if (month === 0) {
      setMonth(11);
      setYear(year - 1);
    } else {
      setMonth(month - 1);
    }
  };

  const handleNextMonth = () => {
    if (month === 11) {
      setMonth(0);
      setYear(year + 1);
    } else {
      setMonth(month + 1);
    }
  };

  // Handle year selection
  const handleYearChange = (e) => {
    setYear(parseInt(e.target.value, 10));
  };

  // Handle month selection
  const handleMonthChange = (e) => {
    setMonth(parseInt(e.target.value, 10));
  };

  // Close on blur
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

  const calendarDays = generateCalendarDays();
  const selectedDate = value ? parseDateOnly(value) : null;

  // Generate year options (18-100 years ago from today)
  const today = new Date();
  const yearOptions = [];
  for (let i = today.getFullYear(); i >= today.getFullYear() - 100; i--) {
    yearOptions.push(i);
  }

  return (
    <div>
      <div className="relative" ref={containerRef}>
        <button
          ref={triggerRef}
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          onBlur={handleTriggerBlur}
          className={`h-12 w-full rounded-xl border bg-white px-4 text-sm outline-none transition flex items-center gap-3 ${
            error
              ? "border-red-500 bg-red-50 text-red-900 focus:border-red-500 focus:ring-4 focus:ring-red-500/20"
              : "border-slate-200 text-slate-900 shadow-sm focus:border-brand-500 focus:shadow-glow focus:ring-4 focus:ring-brand-500/20"
          }`}
        >
          <Calendar className="h-4 w-4 flex-shrink-0 text-slate-400" strokeWidth={2} />
          <span className={value ? "text-slate-900" : "text-slate-400"}>
            {formatDate(value)}
          </span>
        </button>

        {/* Calendar Popover */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.15, ease: [0.22, 1, 0.36, 1] }}
              className="absolute top-full z-50 mt-2 w-80 rounded-2xl border border-slate-200 bg-white shadow-xl"
            >
              <div className="p-4">
                {/* Header with Month/Year navigation */}
                <div className="mb-4 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={handlePrevMonth}
                    className="rounded-lg p-2 text-slate-600 transition hover:bg-slate-100"
                  >
                    <ChevronLeft className="h-4 w-4" strokeWidth={2} />
                  </button>

                  <div className="flex items-center gap-3">
                    <select
                      value={month}
                      onChange={handleMonthChange}
                      className="cursor-pointer appearance-none rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-900 outline-none transition hover:border-slate-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
                    >
                      {[
                        "January",
                        "February",
                        "March",
                        "April",
                        "May",
                        "June",
                        "July",
                        "August",
                        "September",
                        "October",
                        "November",
                        "December"
                      ].map((m, idx) => (
                        <option key={m} value={idx}>
                          {m}
                        </option>
                      ))}
                    </select>

                    <select
                      value={year}
                      onChange={handleYearChange}
                      className="cursor-pointer appearance-none rounded-lg border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-900 outline-none transition hover:border-slate-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
                    >
                      {yearOptions.map((y) => (
                        <option key={y} value={y}>
                          {y}
                        </option>
                      ))}
                    </select>
                  </div>

                  <button
                    type="button"
                    onClick={handleNextMonth}
                    className="rounded-lg p-2 text-slate-600 transition hover:bg-slate-100"
                  >
                    <ChevronRight className="h-4 w-4" strokeWidth={2} />
                  </button>
                </div>

                {/* Day headers */}
                <div className="mb-2 grid grid-cols-7 gap-2 text-center">
                  {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map((day) => (
                    <div
                      key={day}
                      className="text-xs font-medium text-slate-400 py-2"
                    >
                      {day}
                    </div>
                  ))}
                </div>

                {/* Calendar grid */}
                <div className="mb-4 grid grid-cols-7 gap-2">
                  {calendarDays.map((day, idx) => {
                    if (day === null) {
                      return (
                        <div
                          key={`empty-${idx}`}
                          className="aspect-square rounded-lg"
                        />
                      );
                    }

                    const cellDate = new Date(year, month, day);
                    const isSelected =
                      selectedDate &&
                      cellDate.toDateString() === selectedDate.toDateString();
                    const isFuture = cellDate > new Date();

                    return (
                      <button
                        key={day}
                        type="button"
                        onClick={() => handleSelectDate(day)}
                        disabled={isFuture}
                        className={`aspect-square rounded-lg text-sm font-medium transition ${
                          isSelected
                            ? "bg-gradient-to-br from-brand-500 to-brand-600 text-white shadow-lg shadow-brand-500/30"
                            : isFuture
                            ? "cursor-not-allowed text-slate-300"
                            : "text-slate-700 hover:bg-slate-100 active:bg-slate-200"
                        }`}
                      >
                        {day}
                      </button>
                    );
                  })}
                </div>

                {/* Footer buttons */}
                <div className="flex gap-2 border-t border-slate-200 pt-3">
                  <button
                    type="button"
                    onClick={handleToday}
                    className="flex-1 rounded-lg px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-100 active:bg-slate-200"
                  >
                    Today
                  </button>
                  <button
                    type="button"
                    onClick={handleClear}
                    className="flex-1 rounded-lg px-3 py-2 text-xs font-medium text-slate-600 transition hover:bg-slate-100 active:bg-slate-200"
                  >
                    Clear
                  </button>
                </div>
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
