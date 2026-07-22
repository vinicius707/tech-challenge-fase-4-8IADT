import type { NextConfig } from "next";

import { apiRewrites } from "./proxy.mjs";

const nextConfig: NextConfig = {
  async rewrites() {
    return apiRewrites(process.env.BACKEND_URL);
  },
};

export default nextConfig;
