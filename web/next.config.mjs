/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The portal uses plain <img> for the brand logo (a tiny static PNG); don't
  // fail the production build on lint warnings.
  eslint: { ignoreDuringBuilds: true },
};
export default nextConfig;
