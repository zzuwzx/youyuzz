/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#1A1A2E",
        "bg-card": "#16213E",
        accent: "#E94560",
        "accent-secondary": "#0F3460",
        success: "#00C853",
        warning: "#FFD600",
        error: "#FF1744",
        "text-primary": "#E0E0E0",
        "text-secondary": "#9E9E9E",
        divider: "#2A2A4A",
        "vip-gold": "#FFD700",
      },
    },
  },
  plugins: [],
}
