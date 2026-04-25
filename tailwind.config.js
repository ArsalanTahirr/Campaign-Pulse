/** @type {import('tailwindcss').Config} */
const config = {
  darkMode: "class",
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
      },
      keyframes: {
        shake: {
          "0%, 100%": { transform: "translateX(0)" },
          "20%, 60%": { transform: "translateX(-4px)" },
          "40%, 80%": { transform: "translateX(4px)" }
        }
      },
      animation: {
        shake: "shake 0.4s ease-in-out"
      }
    }
  },
  plugins: []
};

module.exports = config;
