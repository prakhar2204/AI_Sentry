import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* ── Output mode ── */
  output: 'export',          // Static HTML export for Cloudflare Pages + Netlify
  trailingSlash: true,       // Consistent URL format for SEO

  /* ── Images ── */
  images: {
    unoptimized: true,        // Required for static export
  },
};

export default nextConfig;
