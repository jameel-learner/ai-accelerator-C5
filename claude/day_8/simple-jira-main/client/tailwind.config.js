/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono: ['"Fira Code"', 'monospace'],
        sans: ['"Fira Sans"', 'sans-serif'],
      },
      colors: {
        primary: {
          light: '#6366F1',
          dark: '#818CF8',
        },
      },
    },
  },
  plugins: [],
}

