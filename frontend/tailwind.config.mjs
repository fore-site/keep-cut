/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        peach: '#fff3e0',
        terracotta: '#e07a5f',
        teal: '#3d5a80',
        coral: '#ee6c4d',
        sky: '#98c1d9',
        body: '#2d2d2d',
      },
      fontFamily: {
        sans: ['var(--font-figtree)', 'sans-serif'],
        display: ['var(--font-outfit)', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
