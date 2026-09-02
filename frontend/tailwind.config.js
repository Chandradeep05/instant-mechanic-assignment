/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0B0F17',
        surface: {
          DEFAULT: '#111827',
          light: '#1F2937',
          lighter: '#374151',
          border: '#1E293B',
        },
        primary: {
          DEFAULT: '#F97316', // Ops Amber/Orange accent
          hover: '#EA580C',
          light: '#FFEDD5',
        },
        critical: {
          DEFAULT: '#EF4444',
          bg: '#450A0A',
          border: '#991B1B',
        },
        high: {
          DEFAULT: '#F59E0B',
          bg: '#451A03',
          border: '#B45309',
        },
        warning: {
          DEFAULT: '#EAB308',
          bg: '#422006',
          border: '#854D0E',
        },
        success: {
          DEFAULT: '#10B981',
          bg: '#022C22',
          border: '#065F46',
        },
        info: {
          DEFAULT: '#3B82F6',
          bg: '#082F49',
          border: '#1E40AF',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      }
    },
  },
  plugins: [],
}
