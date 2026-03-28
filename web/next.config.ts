import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Allow the Python backend URL to be configured at deploy time
  env: {
    BACKEND_URL: process.env.BACKEND_URL || "",
  },
};

export default nextConfig;
