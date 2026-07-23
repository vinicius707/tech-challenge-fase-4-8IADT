import type { NextConfig } from "next";

import { apiRewrites } from "./proxy.mjs";

const nextConfig: NextConfig = {
  experimental: {
    optimizePackageImports: ["lucide-react", "@tanstack/react-query"],
  },
  async rewrites() {
    return apiRewrites(process.env.BACKEND_URL);
  },
};

export default nextConfig;
