import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/hooks/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#1D4E35",
          accent: "#1D9E75",
          soft: "#EAF3E8",
          tint: "#D3EAD4",
        },
      },
      boxShadow: {
        panel: "0 14px 40px rgba(15, 23, 42, 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
