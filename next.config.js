/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Enable Turbopack for faster builds
    turbo: {
      rules: {
        '*.svg': {
          loaders: ['@svgr/webpack'],
          as: '*.js',
        },
      },
    },
  },
  images: {
    domains: ['localhost'],
  },
  // Enable static exports for deployment
  output: 'standalone',
  // Optimize bundle size
  compress: true,
  // Enable React strict mode
  reactStrictMode: true,
  // Enable SWC minification
  swcMinify: true,
}

module.exports = nextConfig
