/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Giphy-inspired accent palette
        giphy: {
          pink: '#ff6666',
          purple: '#9933ff',
          green: '#00ff99',
          blue: '#00ccff',
        },
        ink: {
          900: '#0b0b0f',
          800: '#121218',
          700: '#1a1a23',
          600: '#23232e',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'Avenir', 'Helvetica', 'Arial', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
