import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Allow the Python backend URL to be configured at deploy time
  env: {
    PANOPTICON_BACKEND_URL: process.env.PANOPTICON_BACKEND_URL || "",
  },
};

export default nextConfig;
