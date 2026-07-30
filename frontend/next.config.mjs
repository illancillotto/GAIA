/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async headers() {
    return [
      {
        source: "/",
        headers: [
          {
            key: "Cache-Control",
            value: "no-store, no-cache, must-revalidate, proxy-revalidate",
          },
        ],
      },
    ];
  },
  async redirects() {
    return [
      {
        source: "/accessi",
        destination: "/nas-control",
        permanent: true,
      },
      {
        source: "/accessi/:path*",
        destination: "/nas-control/:path*",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
