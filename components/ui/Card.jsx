export default function Card({ children, className = "" }) {
  return (
    <div
      className={`group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all duration-300 hover:shadow-md hover:border-brand-200 hover:-translate-y-1 ${className}`}
    >
      {/* Subtle top gradient line on hover */}
      <div className="absolute inset-x-0 top-0 h-[2px] w-full bg-gradient-to-r from-transparent via-brand-500 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      {children}
    </div>
  );
}
