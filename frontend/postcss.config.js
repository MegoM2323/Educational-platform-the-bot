export default {
  plugins: {
    tailwindcss: {
      // Optimize Tailwind CSS processing
      corePlugins: {
        // Disable unused core plugins to reduce build time
        // Include only what's needed
      },
    },
    autoprefixer: {
      // Only add prefixes for browsers with > 1% market share
      overrideBrowserslist: [
        '>1%',
        'last 4 versions',
        'Firefox ESR',
        'not ie 11',
      ],
    },
  },
};
