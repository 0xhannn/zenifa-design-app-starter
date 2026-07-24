/**
 * PlayStreet — Tailwind theme tokens (PlayQ-inspired)
 * Drop into tailwind.config.js → theme.extend = { ...require('./design-tokens/playstreet.tailwind') }
 * Live CSS twin lives in static/index.html (:root / data-theme).
 */
module.exports = {
  colors: {
    zen: {
      // Primary — vibrant teal-cyan scale
      cyan: {
        50:  '#F0FCFF',
        100: '#D9F7FF',
        200: '#B3EFFF',
        300: '#7AE3FF',
        400: '#3DD4FF',
        500: '#00D4FF', // primary brand
        600: '#00C4FF', // mid (nav active / chips)
        700: '#00A3CC', // deep teal-cyan
        800: '#007A9E',
        900: '#005A75',
        950: '#003D52',
        bright: '#00E5FF',
        glow:  '#5EEBFF',
      },
      // Accent — hot pink / magenta CTA
      pink: {
        50:  '#FFF0F7',
        100: '#FFD6EB',
        200: '#FFADD6',
        300: '#FF7AC0',
        400: '#FF4DA8',
        500: '#FF3D9A', // primary CTA
        600: '#ED007F', // hover / brand kinship
        700: '#C4006A',
        800: '#9A0054',
        soft: '#FF8FD6',
      },
      // Supporting pops
      yellow: {
        400: '#FFE566',
        500: '#FFD93D',
        600: '#F5C400',
      },
      orange: {
        400: '#FF9A5C',
        500: '#FF6B4A', // coral / warning
        600: '#E84E2F',
      },
      purple: {
        300: '#D4B5FF',
        400: '#B794F6',
        500: '#9B6DFF', // soft purple accent
        600: '#7C4DDB',
      },
      lime: {
        400: '#C8F55A',
        500: '#B8F24A', // finish / success
        600: '#95D12A',
      },
      // Neutrals — dark navy + ice / off-white
      ink: {
        DEFAULT: '#0F1A2E',
        soft:    '#1A2B42',
        muted:   '#4A5B6A',
        faint:   '#7A8B9A',
      },
      ice: {
        DEFAULT: '#F4FBFF',
        soft:    '#E8F9FF',
        mid:     '#DFF4FC',
        line:    '#D0E8F5',
      },
      night: {
        DEFAULT: '#0B1B2B',
        elev:    '#152A3D',
        soft:    '#1E3A4F',
        mid:     '#2A4A62',
        line:    'rgba(255,255,255,0.08)',
      },
      white: '#FFFFFF',
      black: '#000000',
    },
  },

  fontFamily: {
    display: ['Nunito', 'system-ui', 'sans-serif'],
    body:    ['"Nunito Sans"', 'system-ui', 'sans-serif'],
  },

  fontSize: {
    'display': ['clamp(2.4rem, 5.5vw, 3.75rem)', { lineHeight: '1.02', letterSpacing: '-0.03em', fontWeight: '800' }],
    'h2':      ['clamp(1.75rem, 4vw, 2.5rem)', { lineHeight: '1.1', letterSpacing: '-0.02em', fontWeight: '800' }],
    'h3':      ['1.35rem', { lineHeight: '1.25', letterSpacing: '-0.01em', fontWeight: '700' }],
    'body':    ['1rem', { lineHeight: '1.6', fontWeight: '500' }],
    'sm':      ['0.875rem', { lineHeight: '1.5', fontWeight: '500' }],
    'label':   ['0.75rem', { lineHeight: '1.2', letterSpacing: '0.04em', fontWeight: '700' }],
  },

  borderRadius: {
    zen: {
      sm:   '10px',
      md:   '16px',
      lg:   '20px',
      xl:   '24px',
      '2xl': '32px',
      pill: '9999px',
    },
  },

  boxShadow: {
    'zen-sm':    '0 2px 10px rgba(0, 90, 130, 0.06)',
    'zen-md':    '0 8px 24px rgba(0, 90, 130, 0.10)',
    'zen-lg':    '0 16px 40px rgba(0, 70, 110, 0.14)',
    'zen-float': '0 12px 32px rgba(0, 196, 255, 0.18)',
    'zen-cta':   '0 8px 28px rgba(237, 0, 127, 0.35)',
    'zen-cta-lg':'0 14px 40px rgba(237, 0, 127, 0.55)',
    'zen-glow':  '0 0 0 4px rgba(0, 196, 255, 0.25)',
    'zen-pink-ring': '0 0 0 4px rgba(255, 61, 154, 0.25)',
    'zen-sticker': '3px 3px 0 #0F1A2E',
  },

  backgroundImage: {
    'zen-sky':
      'radial-gradient(ellipse 80% 60% at 85% 40%, rgba(255,61,154,0.18) 0%, transparent 55%), radial-gradient(ellipse 50% 40% at 15% 80%, rgba(255,229,102,0.22) 0%, transparent 50%), linear-gradient(165deg, #5EEBFF 0%, #00D4FF 25%, #00C4FF 55%, #00A3CC 100%)',
    'zen-ice':
      'linear-gradient(165deg, #E8F9FF 0%, #F4FBFF 45%, #DFF4FC 100%)',
    'zen-night':
      'linear-gradient(165deg, #0B1B2B 0%, #123047 50%, #0A2233 100%)',
    'zen-cta':
      'linear-gradient(135deg, #FF3D9A 0%, #ED007F 100%)',
    'zen-blob':
      'radial-gradient(circle at 40% 35%, #FFE566 0%, #00E5FF 45%, #FF3D9A 100%)',
  },

  transitionTimingFunction: {
    bounce: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
    soft:   'cubic-bezier(0.22, 1, 0.36, 1)',
  },

  transitionDuration: {
    zen: '280ms',
    fast: '150ms',
  },

  // Semantic aliases (use in @apply / plugins)
  // light: bg-zen-ice text-zen-ink
  // dark:  bg-zen-night text-white
  // cta:   bg-zen-pink-500 hover:bg-zen-pink-600 text-white
  // brand: bg-zen-cyan-500 text-zen-ink
};
