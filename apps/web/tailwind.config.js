/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#08090d",
        foreground: "#f3f4f6",
        card: "#12141c",
        border: "#1e2230",
        primary: {
          DEFAULT: "#6366f1",
          hover: "#4f46e5",
        },
        accent: {
          cyan: "#06b6d4",
          purple: "#a855f7",
          pink: "#ec4899",
          emerald: "#10b981",
        }
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-spin': 'spin 12s linear infinite',
      }
    },
  },
  plugins: [],
};
