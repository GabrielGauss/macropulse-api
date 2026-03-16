/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['"Inter"', 'system-ui', 'sans-serif'],
        display: ['"Inter"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        surface: {
          0: '#0a0a0a',
          1: '#111111',
          2: '#191919',
          3: '#222222',
          4: '#2a2a2a',
        },
        border: {
          DEFAULT: '#1f1f1f',
          2: '#2a2a2a',
        },
        accent: {
          green:  '#22c55e',
          red:    '#ef4444',
          amber:  '#f59e0b',
          blue:   '#3b82f6',
        },
        regime: {
          expansion:  '#22c55e',
          recovery:   '#3b82f6',
          tightening: '#f59e0b',
          risk_off:   '#ef4444',
        },
      },
    },
  },
  plugins: [],
};
