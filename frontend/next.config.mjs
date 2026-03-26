/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
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
