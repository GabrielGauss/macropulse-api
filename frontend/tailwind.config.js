/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['"JetBrains Mono"', 'monospace'],
        display: ['"JetBrains Mono"', 'monospace'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        none: '0', sm: '0', DEFAULT: '0', md: '0',
        lg: '0', xl: '0', '2xl': '0', '3xl': '0', full: '0',
      },
      colors: {
        surface: {
          0: '#080808',
          1: '#0f0f0f',
          2: '#141414',
          3: '#1e1e1e',
          4: '#282828',
        },
        border: {
          DEFAULT: '#1a1a1a',
          2: '#252525',
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
