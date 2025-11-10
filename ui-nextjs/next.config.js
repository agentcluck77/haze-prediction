/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  images: {
    domains: [],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  webpack: (config, { isServer }) => {
    // Exclude maplibre-gl from SSR bundle
    if (isServer) {
      config.externals = [...(config.externals || []), 'maplibre-gl'];
    }

    return config;
  },
}

module.exports = nextConfig

