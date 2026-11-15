/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        studio: "var(--bg-studio)",
        ink: {
          DEFAULT: "var(--ink-primary)",
          muted: "var(--ink-muted)",
          subtle: "var(--ink-subtle)",
        },
        hairline: "var(--border-hairline)",
        pill: "var(--pill-inactive)",
        brand: "var(--accent-brand)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
