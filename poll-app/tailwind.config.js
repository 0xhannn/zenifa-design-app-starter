/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        zen: {
          cyan: '#00C4FF',
          pink: '#FF3D9A',
          yellow: '#FFE566',
          lime: '#B8F24A',
          ink: '#0F1A2E',
          ice: '#F4FBFF',
          night: '#0B1B2B',
        },
      },
      fontFamily: {
        heading: ['Nunito', 'system-ui', 'sans-serif'],
        body: ['Nunito Sans', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        cta: '0 8px 28px rgba(237, 0, 127, 0.35)',
        cyan: '0 8px 28px rgba(0, 196, 255, 0.28)',
      },
      borderRadius: {
        xl2: '1.25rem',
      },
    },
  },
  plugins: [],
}
