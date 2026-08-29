import path from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  webpack(config, { webpack }) {
    config.plugins.push(new webpack.NormalModuleReplacementPlugin(
      /^@\/components\/catasto\/gis\/MapContainer$/,
      path.join(rootDir, "src/components/catasto/gis/TerritorioMapExperience.tsx"),
    ));
    return config;
  },
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
