tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        parchment: '#FDFBF7',
        ink: {
          light: '#2D3748',
          DEFAULT: '#1A202C',
          dark: '#0F172A',
          darker: '#0a0e17'
        },
        willGold: {
          DEFAULT: '#C5A880',
          hover: '#B39263',
          light: '#e3d2be',
          dark: '#8c7047'
        },
        crimsonWax: {
          DEFAULT: '#8B1E1E',
          hover: '#701515',
          light: '#a83232'
        }
      },
      fontFamily: {
        cinzel: ['Cinzel', 'Playfair Display', 'Georgia', 'serif'],
        serif: ['Cinzel', 'Playfair Display', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'Courier New', 'monospace']
      }
    }
  }
};
