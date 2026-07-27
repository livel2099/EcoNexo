import path from "node:path";
import { fileURLToPath } from "node:url";

const isCloudflareDemo = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
const isStaticExport = isCloudflareDemo || process.env.NEXT_PUBLIC_STATIC_EXPORT === "true";
const projectRoot = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: isStaticExport ? "export" : "standalone",
  trailingSlash: isStaticExport,
  images: { unoptimized: isStaticExport },
  poweredByHeader: false,

  // Keep Next.js anchored to apps/web even when another package-lock.json
  // exists higher in the repository. This removes the ambiguous workspace
  // root warning and keeps file tracing deterministic on Windows and CI.
  outputFileTracingRoot: projectRoot,
};

export default nextConfig;
