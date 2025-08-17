/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        // Elegant black and white theme
        primary: '#000000',
        secondary: '#111111',
        tertiary: '#1a1a1a',
        surface: {
          DEFAULT: 'rgba(0, 0, 0, 0.95)',
          light: 'rgba(0, 0, 0, 0.85)',
          dark: 'rgba(0, 0, 0, 0.98)',
          card: 'rgba(20, 20, 20, 0.95)',
          overlay: 'rgba(0, 0, 0, 0.8)'
        },
        accent: {
          50: '#f8f9fa',
          100: '#f1f3f4',
          200: '#e8eaed',
          300: '#dadce0',
          400: '#bdc1c6',
          500: '#9aa0a6',
          600: '#80868b',
          700: '#5f6368',
          800: '#3c4043',
          900: '#202124',
          DEFAULT: '#ffffff',
          hover: '#f8f9fa',
          muted: '#9aa0a6'
        },
        text: {
          primary: '#ffffff',
          secondary: '#e8eaed',
          muted: '#9aa0a6',
          accent: '#bdc1c6',
          inverse: '#202124'
        },
        border: {
          primary: 'rgba(255, 255, 255, 0.15)',
          secondary: 'rgba(255, 255, 255, 0.1)',
          accent: 'rgba(255, 255, 255, 0.25)',
          focus: 'rgba(255, 255, 255, 0.35)',
          subtle: 'rgba(255, 255, 255, 0.08)'
        },
        glass: {
          light: 'rgba(255, 255, 255, 0.03)',
          medium: 'rgba(255, 255, 255, 0.08)',
          dark: 'rgba(0, 0, 0, 0.6)',
          card: 'rgba(255, 255, 255, 0.02)'
        }
      },
      backgroundImage: {
        'gradient-main': 'linear-gradient(135deg, #000000 0%, #111111 50%, #1a1a1a 100%)',
        'gradient-elegant': 'linear-gradient(135deg, #000000 0%, #202124 100%)',
        'gradient-card': 'linear-gradient(135deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0.01))',
        'gradient-text': 'linear-gradient(135deg, #ffffff, #e8eaed)',
        'gradient-border': 'linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05))'
      },
      backdropBlur: {
        xs: '2px',
        'glass': '20px'
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.5)',
        'elegant': '0 8px 25px rgba(0, 0, 0, 0.3)',
        'elegant-lg': '0 20px 60px rgba(0, 0, 0, 0.4)',
        'subtle': '0 4px 16px rgba(0, 0, 0, 0.2)',
        'card': '0 12px 40px rgba(0, 0, 0, 0.6)',
        'card-hover': '0 16px 48px rgba(0, 0, 0, 0.8)',
        'glow': '0 0 6px rgba(255, 255, 255, 0.2)',
        'glow-strong': '0 0 12px rgba(255, 255, 255, 0.3)',
        'inner': 'inset 0 1px 2px rgba(0, 0, 0, 0.1)'
      },
      animation: {
        'fadeInUp': 'fadeInUp 0.6s ease-out forwards',
        'float': 'float 3s ease-in-out infinite',
        'pulse-slow': 'pulse 3s ease-in-out infinite'
      },
      keyframes: {
        fadeInUp: {
          '0%': {
            opacity: '0',
            transform: 'translateY(30px)'
          },
          '100%': {
            opacity: '1',
            transform: 'translateY(0)'
          }
        },
        float: {
          '0%, 100%': {
            transform: 'translateY(0px)'
          },
          '50%': {
            transform: 'translateY(-10px)'
          }
        }
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem'
      },
      borderRadius: {
        '4xl': '2rem'
      }
    }
  },
  plugins: [],
};
