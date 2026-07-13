const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

module.exports = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ]
  },
}
