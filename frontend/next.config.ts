import type { NextConfig } from "next";

const isMock = process.env.NEXT_PUBLIC_MOCK === 'true';

const nextConfig: NextConfig = {
  // Static export for GitHub Pages
  output: isMock ? 'export' : undefined,
  basePath: isMock ? '/pro-nlp-finalproject-nlp-01' : '',
  assetPrefix: isMock ? '/pro-nlp-finalproject-nlp-01/' : '',
  images: {
    unoptimized: true,
  },
  trailingSlash: isMock ? true : false,
};

export default nextConfig;
