/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1c1f26",
        paper: "#f7f7f5",
        panel: "#ffffff",
        line: "#e2e2df",
        accent: {
          DEFAULT: "#2a6f5e",
          dark: "#1f5548",
        },
        warn: "#b5502a",
        muted: "#6b6f76",
      },
      fontFamily: {
        mono: ["SF Mono", "JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
