import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#f5f3ef',
        s1: '#edeae5',
        s2: '#e5e1db',
        s3: '#dad6cf',
        border: 'rgba(28,18,8,0.08)',
        'border-mid': 'rgba(28,18,8,0.14)',
        ink: '#1c1917',
        ink2: '#6b6560',
        ink3: '#a8a29e',
        red: '#c8102e',
        amber: '#c47a0a',
        blue: '#1d3a6e',
        green: '#166534',
        'scene-bg': '#0d0c12',
        'scene-mid': '#1a1720',
        'scene-near': '#11101a',
      },
      fontFamily: {
        display: ['"Bebas Neue"', 'Impact', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display-xl': ['72px', { lineHeight: '1', letterSpacing: '0.02em' }],
        'display-lg': ['56px', { lineHeight: '1', letterSpacing: '0.02em' }],
        'display-md': ['40px', { lineHeight: '1', letterSpacing: '0.02em' }],
        'display-sm': ['28px', { lineHeight: '1', letterSpacing: '0.02em' }],
        'display-xs': ['22px', { lineHeight: '1', letterSpacing: '0.04em' }],
      },
      borderRadius: {
        card: '6px',
        btn: '4px',
      },
    },
  },
  plugins: [],
}

export default config
