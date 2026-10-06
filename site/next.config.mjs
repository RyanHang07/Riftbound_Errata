// Static export: the site is plain files on Vercel, no server code (A33).
import createMDX from "@next/mdx";

const withMDX = createMDX({});

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  pageExtensions: ["ts", "tsx", "mdx"],
  images: { unoptimized: true },
  trailingSlash: true,
};

export default withMDX(nextConfig);
