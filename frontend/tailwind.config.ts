import type { Config } from 'tailwindcss';
import typography from '@tailwindcss/typography';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            maxWidth: 'none',
            color: '#374151',
            a: {
              color: '#4f46e5',
              '&:hover': {
                color: '#4338ca',
              },
            },
            code: {
              color: '#dc2626',
              padding: '0.2em 0.4em',
              backgroundColor: '#f3f4f6',
              borderRadius: '0.25em',
              '&::before': {
                content: '""',
              },
              '&::after': {
                content: '""',
              },
            },
            'code::before': {
              content: '""',
            },
            'code::after': {
              content: '""',
            },
            pre: {
              backgroundColor: '#1f2937',
              color: '#f3f4f6',
              overflowX: 'auto',
            },
            'pre code': {
              backgroundColor: 'transparent',
              color: 'inherit',
              padding: '0',
            },
            img: {
              maxWidth: '100%',
              height: 'auto',
            },
            table: {
              borderCollapse: 'collapse',
            },
            thead: {
              backgroundColor: '#f3f4f6',
            },
            'th, td': {
              padding: '0.75rem 1rem',
              borderColor: '#e5e7eb',
            },
          },
        },
        sm: {
          css: {
            fontSize: '0.875rem',
            h1: { fontSize: '1.5rem' },
            h2: { fontSize: '1.25rem' },
            h3: { fontSize: '1.1rem' },
          },
        },
      },
    },
  },
  plugins: [typography],
};

export default config;
