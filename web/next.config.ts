import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Allow the Python backend URL to be configured at deploy time
  env: {
    BACKEND_URL: process.env.BACKEND_URL || "",
  },
  // CesiumJS requires static assets and webpack config
  webpack: (config, { isServer, webpack }) => {
    if (!isServer) {
      // Copy Cesium static assets to public/cesium at build time
      const CopyPlugin = require("copy-webpack-plugin");
      const path = require("path");

      config.plugins.push(
        new CopyPlugin({
          patterns: [
            {
              from: path.join(__dirname, "node_modules/cesium/Build/Cesium/Workers"),
              to: path.join(__dirname, "public/cesium/Workers"),
            },
            {
              from: path.join(__dirname, "node_modules/cesium/Build/Cesium/ThirdParty"),
              to: path.join(__dirname, "public/cesium/ThirdParty"),
            },
            {
              from: path.join(__dirname, "node_modules/cesium/Build/Cesium/Assets"),
              to: path.join(__dirname, "public/cesium/Assets"),
            },
            {
              from: path.join(__dirname, "node_modules/cesium/Build/Cesium/Widgets"),
              to: path.join(__dirname, "public/cesium/Widgets"),
            },
          ],
        })
      );

      // Define Cesium base URL
      config.plugins.push(
        new webpack.DefinePlugin({
          CESIUM_BASE_URL: JSON.stringify("/cesium"),
        })
      );
    }
    return config;
  },
};

export default nextConfig;
