/** @type {import('tailwindcss').Config} */
const config = {
  content: [
    "./app/**/*.{js,jsx,mdx}",
    "./components/**/*.{js,jsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          500: "#4f46e5",
          600: "#4338ca",
          700: "#3730a3"
        },
        pulseTeal: "#0D9488",
        pulseBlue: "#2563EB"
      },
      boxShadow: {
        glow: "0 0 0 4px rgba(79,70,229,0.15)"
      }
    }
  },
  plugins: []
};

module.exports = config;
